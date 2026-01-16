"""
SICAR Class Module.

This module defines a class representing the Sicar system for managing environmental rural properties in Brazil.

Classes:
    Sicar: Class representing the Sicar system.
"""

import io
import os
import ssl
import time
import random
import httpx
from PIL import Image, UnidentifiedImageError
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import Dict
from pathlib import Path
from urllib.parse import urlencode
import warnings

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message="ssl.PROTOCOL_TLSv1_2 is deprecated"
)

from SICAR.drivers import Captcha, Tesseract
from SICAR.state import State
from SICAR.url import Url
from SICAR.polygon import Polygon
from SICAR.exceptions import (
    UrlNotOkException,
    PolygonNotValidException,
    StateCodeNotValidException,
    FailedToDownloadCaptchaException,
    FailedToDownloadPolygonException,
    FailedToGetReleaseDateException,
)


class Sicar(Url):
    """
    Class representing the Sicar system.

    Sicar is a system for managing environmental rural properties in Brazil.

    It inherits from the Url class to provide access to URLs related to the Sicar system.

    Attributes:
        _driver (Captcha): The driver used for handling captchas. Default is Tesseract.
    """

    def __init__(
        self,
        driver: Captcha = Tesseract,
        headers: Dict = None,
    ):
        """
        Initialize an instance of the Sicar class.

        Parameters:
            driver (Captcha): The driver used for handling captchas. Default is Tesseract.
            headers (Dict): Additional headers for HTTP requests. Default is None.

        Returns:
            None
        """
        self._driver = driver()
        self._create_session(headers=headers)
        self._initialize_cookies()

    def _parse_release_dates(self, response: bytes) -> Dict:
        """
        Parse raw html getting states and release date.

        Parameters:
            response (bytes): The request content as byte string containing html page from SICAR with release dates per state

        Returns:
            Dict: A dict containing state sign as keys and parsed update date as value.
        """
        html_content = response.decode("utf-8")

        soup = BeautifulSoup(html_content, "html.parser")

        state_dates = {}

        for state_block in soup.find_all("div", class_="listagem-estados"):
            button_tag = state_block.find(
                "button", class_="btn-abrir-modal-download-base-poligono"
            )
            state = button_tag.get("data-estado") if button_tag else None

            date_tag = state_block.find("div", class_="data-disponibilizacao")
            date = date_tag.get_text(strip=True) if date_tag else None

            if state in iter(State) and date:
                state_dates[State(state)] = date

        return state_dates

    def _create_session(self, headers: Dict = None):
        """
        Create a new session for making HTTP requests.

        Parameters:
            headers (Dict): Additional headers for the session. Default is None.

        Note:
            The SSL certificate verification is disabled by default using `verify=context`. This allows connections to servers
            with self-signed or invalid certificates. Disabling SSL certificate verification can expose your application to
            security risks, such as man-in-the-middle attacks. If the server has a valid SSL certificate issued by a trusted
            certificate authority, you can remove the `verify=context` parameter to enable SSL certificate verification by
            default.

        Returns:
            None
        """

        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.set_ciphers("RSA+AESGCM:RSA+AES:!aNULL:!MD5:!DSS")

        # Timeout aumentado para 120s (SICAR pode ser muito lento)
        self._session = httpx.Client(
            verify=context,
            timeout=httpx.Timeout(120.0, connect=30.0)
        )
        self._session.headers.update(
            headers
            if isinstance(headers, dict)
            else {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "close",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            }
        )

    def _initialize_cookies(self):
        """
        Initialize cookies by making the initial request and accepting any redirections.

        This method is intended to be called in the constructor to set up the session cookies.

        Returns:
            None
        """
        self._get(self._INDEX)

    def _get(self, url: str, *args, **kwargs):
        """
        Send a GET request to the specified URL using the session.

        Parameters:
            url (str): The URL to send the GET request to.
            *args: Variable-length positional arguments.
            **kwargs: Variable-length keyword arguments.

        Returns:
            requests.Response: The response from the GET request.

        Raises:
            UrlNotOkException: If the response from the GET request is not OK (status code is not 200).
        """
        response = self._session.get(url=url, *args, **kwargs)

        if response.status_code not in [httpx.codes.OK, httpx.codes.FOUND]:
            raise UrlNotOkException(url)

        return response

    def _download_captcha(self) -> Image:
        """
        Download a captcha image from the SICAR system.

        Returns:
            Image: The captcha image.

        Raises:
            FailedToDownloadCaptchaException: If the captcha image fails to download.
        """
        url = f"{self._RECAPTCHA}?{urlencode({'id': int(random.random() * 1000000)})}"
        response = self._get(url)

        if response.status_code != httpx.codes.OK:
            raise FailedToDownloadCaptchaException()

        try:
            captcha = Image.open(io.BytesIO(response.content))
        except UnidentifiedImageError as error:
            raise FailedToDownloadCaptchaException() from error

        return captcha

    def _download_polygon(
        self,
        state: State,
        polygon: Polygon,
        captcha: str,
        folder: str,
        chunk_size: int = 1024,
    ) -> Path:
        """
        Download polygon for the specified state.

        Parameters:
            state (State | str): The state for which to download the files. It can be either a `State` enum value or a string representing the state's abbreviation.
            polygon (Polygon | str): The polygon to download.
            captcha (str): The captcha value for verification.
            folder (str): The folder path where the polygon will be saved.
            chunk_size (int, optional): The size of each chunk to download. Defaults to 1024.

        Returns:
            Path: The path to the downloaded polygon.

        Raises:
            FailedToDownloadPolygonException: If the polygon download fails.

        Note:
            This method performs the polygon download by making a GET request to the polygon URL with the specified
            state code and captcha. The response is then streamed and saved to a file in chunks. A progress bar is displayed
            during the download. The downloaded file path is returned.
        """

        query = urlencode(
            {"idEstado": state.value, "tipoBase": polygon.value, "ReCaptcha": captcha}
        )

        with self._session.stream("GET", f"{self._DOWNLOAD_BASE}?{query}") as response:
            try:
                if response.status_code != httpx.codes.OK:
                    raise UrlNotOkException(f"{self._DOWNLOAD_BASE}?{query}")
            except UrlNotOkException as error:
                raise FailedToDownloadPolygonException() from error

            content_length = int(response.headers.get("Content-Length", 0))

            content_type = response.headers.get("Content-Type", "")

            if content_length == 0 or not content_type.startswith("application/zip"):
                raise FailedToDownloadPolygonException()
            path = Path(
                os.path.join(folder, f"{state.value}_{polygon.value}")
            ).with_suffix(".zip")

            with open(path, "wb") as fd:
                with tqdm(
                    total=content_length,
                    unit="iB",
                    unit_scale=True,
                    desc=f"Downloading polygon '{polygon.value}' for state '{state.value}'",
                ) as progress_bar:
                    for chunk in response.iter_bytes():
                        fd.write(chunk)
                        progress_bar.update(len(chunk))
        return path

    def download_state(
        self,
        state: State | str,
        polygon: Polygon | str,
        folder: Path | str = Path("temp"),
        tries: int = 25,
        debug: bool = False,
        chunk_size: int = 1024,
    ) -> Path | bool:
        """
        Download the polygon or other output format for the specified state.

        Parameters:
            state (State | str): The state for which to download the files. It can be either a `State` enum value or a string representing the state's abbreviation.
            polygon (Polygon | str): The polygon to download the files. It can be either a `Polygon` enum value or a string representing the polygon's.
            folder (Path | str, optional): The folder path where the downloaded data will be saved. Defaults to "temp".
            tries (int, optional): The number of attempts to download the data. Defaults to 25.
            debug (bool, optional): Whether to print debug information. Defaults to False.
            chunk_size (int, optional): The size of each chunk to download. Defaults to 1024.

        Returns:
            Path | bool: The path to the downloaded data if successful, or False if download fails.

        Note:
            This method attempts to download the polygon for the specified state.
            It tries multiple times, using a captcha for verification. The downloaded data is saved to the specified folder.
            The method returns the path to the downloaded data if successful, or False if the download fails after the specified number of tries.
        """
        if isinstance(state, str):
            try:
                state = State(state.upper())
            except ValueError as error:
                raise StateCodeNotValidException(state) from error

        if isinstance(polygon, str):
            try:
                polygon = Polygon(polygon.upper())
            except ValueError as error:
                raise PolygonNotValidException(polygon) from error

        Path(folder).mkdir(parents=True, exist_ok=True)

        captcha = ""
        info = f"'{polygon.value}' for '{state.value}'"

        while tries > 0:
            try:
                captcha = self._driver.get_captcha(self._download_captcha())

                if len(captcha) == 5:
                    if debug:
                        print(
                            f"[{tries:02d}] - Requesting {info} with captcha '{captcha}'"
                        )

                    return self._download_polygon(
                        state=state,
                        polygon=polygon,
                        captcha=captcha,
                        folder=folder,
                        chunk_size=chunk_size,
                    )
                elif debug:
                    print(
                        f"[{tries:02d}] - Invalid captcha '{captcha}' to request {info}"
                    )
            except (
                FailedToDownloadCaptchaException,
                FailedToDownloadPolygonException,
            ) as error:
                if debug:
                    print(f"[{tries:02d}] - {error} When requesting {info}")
            finally:
                tries -= 1
                time.sleep(random.random() + random.random())

        return False

    def download_country(
        self,
        polygon: Polygon | str,
        folder: Path | str = Path("brazil"),
        tries: int = 25,
        debug: bool = False,
        chunk_size: int = 1024,
    ):
        """
        Download polygon for the entire country.

        Parameters:
            polygon (Polygon | str): The polygon to download the files. It can be either a `Polygon` enum value or a string representing the polygon's.
            folder (Path | str, optional): The folder path where the downloaded files will be saved. Defaults to 'brazil'.
            tries (int, optional): The number of download attempts allowed per state. Defaults to 25.
            debug (bool, optional): Whether to enable debug mode with additional print statements. Defaults to False.
            chunk_size (int, optional): The size of each chunk to download. Defaults to 1024.

        Returns:
            Dict: A dictionary containing the results of the download operation.
                The keys are the state abbreviations, and the values are dictionaries representing the results of downloading each state.
                Each state's dictionary follows the same structure as the result of the `download_state` method.
                If a download fails for a state the corresponding value will be False.
        """
        result = {}
        for state in State:
            Path(os.path.join(folder, f"{state}")).mkdir(parents=True, exist_ok=True)

            result[str(state)] = self.download_state(
                state=state,
                polygon=polygon,
                folder=folder,
                tries=tries,
                debug=debug,
                chunk_size=chunk_size,
            )

    def search_by_car_number(self, car_number: str) -> Dict:
        """
        Search for a property by CAR number.

        Parameters:
            car_number (str): The CAR number to search for (e.g., "SP-3538709-4861E981046E49BC81720C879459E554").

        Returns:
            Dict: Property information including internal ID, geometry, and metadata.

        Raises:
            Exception: If the search fails or property not found.
        """
        search_url = f"{self._BASE}/imoveis/search?text={car_number}"
        
        try:
            response = self._get(search_url)
            data = response.json()
            
            if data.get("features") and len(data["features"]) > 0:
                return data["features"][0]
            else:
                raise Exception(f"Property not found for CAR number: {car_number}")
                
        except Exception as error:
            raise Exception(f"Failed to search CAR number {car_number}: {error}") from error

    def download_by_car_number(
        self,
        car_number: str,
        folder: Path | str = Path("temp"),
        tries: int = 25,
        debug: bool = False,
        chunk_size: int = 1024,
    ) -> Path | bool:
        """
        Download shapefile for a specific property by CAR number.

        Parameters:
            car_number (str): The CAR number to download (e.g., "SP-3538709-4861E981046E49BC81720C879459E554").
            folder (Path | str, optional): The folder path where the downloaded data will be saved. Defaults to "temp".
            tries (int, optional): The number of attempts to download the data. Defaults to 25.
            debug (bool, optional): Whether to print debug information. Defaults to False.
            chunk_size (int, optional): The size of each chunk to download. Defaults to 1024.

        Returns:
            Path | bool: The path to the downloaded data if successful, or False if download fails.

        Note:
            This method first searches for the property to get the internal ID,
            then downloads the shapefile using captcha verification.
        """
        # Search for property
        property_data = self.search_by_car_number(car_number)
        internal_id = property_data.get("id")
        
        if debug:
            print(f"Property data: {property_data}")
            print(f"Internal ID: {internal_id}")
        
        if not internal_id:
            raise Exception(f"Internal ID not found for CAR number: {car_number}")
        
        # Create folder
        Path(folder).mkdir(parents=True, exist_ok=True)
        
        # Download with captcha retry
        captcha = ""
        info = f"property CAR '{car_number}'"
        
        while tries > 0:
            try:
                captcha = self._driver.get_captcha(self._download_captcha())

                if len(captcha) == 5:
                    if debug:
                        print(f"[{tries:02d}] - Requesting {info} with captcha '{captcha}'")

                    return self._download_property_shapefile(
                        internal_id=internal_id,
                        car_number=car_number,
                        captcha=captcha,
                        folder=folder,
                        chunk_size=chunk_size,
                        debug=debug,
                    )
                elif debug:
                    print(f"[{tries:02d}] - Invalid captcha '{captcha}' to request {info}")
                    
            except (
                FailedToDownloadCaptchaException,
                FailedToDownloadPolygonException,
            ) as error:
                if debug:
                    print(f"[{tries:02d}] - {error} When requesting {info}")
            finally:
                tries -= 1
                time.sleep(random.random() + random.random())

        return False

    def _download_property_shapefile(
        self,
        internal_id: str,
        car_number: str,
        captcha: str,
        folder: Path | str,
        chunk_size: int = 1024,
        debug: bool = False,
    ) -> Path:
        """
        Download shapefile for a specific property using internal ID and captcha.

        Parameters:
            internal_id (str): The internal SICAR ID for the property.
            car_number (str): The CAR number (used for filename).
            captcha (str): The resolved captcha string.
            folder (Path | str): The folder path where the file will be saved.
            chunk_size (int, optional): The size of each chunk to download. Defaults to 1024.

        Returns:
            Path: The path to the downloaded file.

        Raises:
            FailedToDownloadPolygonException: If the download fails.
        """
        download_url = f"{self._BASE}/imoveis/exportShapeFile?idImovel={internal_id}&ReCaptcha={captcha}"
        
        if debug:
            print(f"Download URL: {download_url}")
            print(f"Trying POST method instead of GET...")
        
        try:
            # Try POST instead of GET (some APIs require POST for downloads)
            response = self._session.post(
                f"{self._BASE}/imoveis/exportShapeFile",
                data={
                    "idImovel": internal_id,
                    "ReCaptcha": captcha
                }
            )
            
            if response.status_code == 200:
                # Check if response is base64 data URL
                content = response.content
                if response.text.startswith("data:application/zip;base64,"):
                    import base64
                    base64_data = response.text.split(",", 1)[1]
                    content = base64.b64decode(base64_data)
                
                # POST worked! Save the file
                sanitized_car = car_number.replace("-", "_")
                file_path = Path(folder) / f"{sanitized_car}.zip"
                
                with open(file_path, "wb") as file:
                    file.write(content)
                
                if debug:
                    print(f"Downloaded successfully via POST: {len(content)} bytes")
                
                return file_path
            else:
                if debug:
                    print(f"POST failed with status {response.status_code}, trying GET...")
            
            # Fallback to GET with streaming
            with self._session.stream("GET", download_url) as stream_response:
                # Check if response is valid
                if stream_response.status_code != 200:
                    if debug:
                        print(f"HTTP {stream_response.status_code}")
                        print(f"Headers: {dict(stream_response.headers)}")
                        try:
                            # Try to read as text
                            content = b""
                            for chunk in stream_response.iter_bytes():
                                content += chunk
                                if len(content) > 1000:
                                    break
                            text = content.decode('utf-8', errors='ignore')
                            print(f"Response (first 500 chars): {text[:500]}")
                        except Exception as e:
                            print(f"Could not read response: {e}")
                    raise FailedToDownloadPolygonException()
                
                # Generate filename
                sanitized_car = car_number.replace("-", "_")
                file_path = Path(folder) / f"{sanitized_car}.zip"
                
                # Check if it's a base64 data URL response
                # Read first chunk to check
                first_chunks = []
                bytes_read = 0
                for chunk in stream_response.iter_bytes(chunk_size=chunk_size):
                    first_chunks.append(chunk)
                    bytes_read += len(chunk)
                    if bytes_read > 100:  # Read enough to detect format
                        break
                
                # Check if base64 data URL
                preview = b"".join(first_chunks)
                if preview.startswith(b"data:application/zip;base64,"):
                    # Read all remaining content
                    remaining = []
                    for chunk in stream_response.iter_bytes(chunk_size=chunk_size):
                        remaining.append(chunk)
                    
                    full_content = b"".join(first_chunks + remaining)
                    text = full_content.decode('utf-8')
                    
                    import base64
                    base64_data = text.split(",", 1)[1]
                    binary_content = base64.b64decode(base64_data)
                    
                    with open(file_path, "wb") as file:
                        file.write(binary_content)
                    
                    if debug:
                        print(f"Downloaded and decoded base64: {len(binary_content)} bytes")
                else:
                    # Regular binary download
                    total_size = int(stream_response.headers.get("content-length", 0))
                    
                    with open(file_path, "wb") as file:
                        # Write first chunks
                        for chunk in first_chunks:
                            file.write(chunk)
                        
                        # Continue with progress bar
                        with tqdm(
                            total=total_size,
                            unit="B",
                            unit_scale=True,
                            desc=f"Downloading property '{car_number}'",
                            initial=bytes_read
                        ) as progress_bar:
                            for chunk in stream_response.iter_bytes(chunk_size=chunk_size):
                                if chunk:
                                    file.write(chunk)
                                    progress_bar.update(len(chunk))
            
            return file_path
            
        except httpx.HTTPStatusError:
            raise FailedToDownloadPolygonException()
        except Exception:
            raise FailedToDownloadPolygonException()

    def get_release_dates(self) -> Dict:
        """
        Get release date for each state in SICAR system.

        Returns:
            Dict: A dict containing state sign as keys and release date as string in dd/mm/yyyy format.

        Raises:
            FailedToGetReleaseDateException: If the page with release date fails to load.
        """
        try:
            response = self._get(f"{self._RELEASE_DATE}")
            return self._parse_release_dates(response.content)
        except UrlNotOkException as error:
            raise FailedToGetReleaseDateException() from error
