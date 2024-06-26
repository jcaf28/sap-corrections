# PATH: src/app/routers/excel_router.py

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import Optional, Union
import os
from datetime import datetime
import shutil
import zipfile

router = APIRouter()

def get_file_path(filename: str, prefix: str = "") -> str:
    """ Helper function to create file path """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"static/results/{prefix}{timestamp}_{filename}"

def create_zip_file(files, zip_filename):
    """ Create a zip file from a list of files """
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))
    return zip_filename

@router.post("/generate_excel/")
async def generate_excel(
    archivo_stocks: Union[UploadFile, str] = File(default="STOCKS_EA_EB_2024_06_06.xlsx"),
    archivo_coois: UploadFile = File(...),
    master_data: Optional[UploadFile] = File(None),
    download_ea: bool = Form(True),
    download_eb: bool = Form(True)
):
    # Define default master data path and temporary save uploaded files
    master_data_path = "prod_files/data/master_data.xlsx"
    temp_coois_path = get_file_path(archivo_coois.filename, "coois_")
    with open(temp_coois_path, "wb") as buffer:
        shutil.copyfileobj(archivo_coois.file, buffer)

    if isinstance(archivo_stocks, UploadFile):
        temp_stocks_path = get_file_path(archivo_stocks.filename, "stocks_")
        with open(temp_stocks_path, "wb") as buffer:
            shutil.copyfileobj(archivo_stocks.file, buffer)
    else:
        temp_stocks_path = f"prod_files/data/{archivo_stocks}"  # Use the default file if string identifier is passed

    if master_data:
        master_data_path = get_file_path(master_data.filename, "master_")
        with open(master_data_path, "wb") as buffer:
            shutil.copyfileobj(master_data.file, buffer)

    # Process files
    from src.app.generar_excel_crosstabs_completo import generar_excel_crosstabs_completo
    result_paths = generar_excel_crosstabs_completo(
        archivo_stocks=temp_stocks_path,
        archivo_coois=temp_coois_path,
        archivo_maestros=master_data_path
    )

    # Create ZIP file if both files are to be downloaded
    if download_ea or download_eb:
        files_to_zip = []
        if download_ea and result_paths[0]:
            files_to_zip.append(result_paths[0])
        if download_eb and result_paths[1]:
            files_to_zip.append(result_paths[1])

        if files_to_zip:
            zip_filename = get_file_path("descarga_EB_y_EA.zip", "zip_")
            create_zip_file(files_to_zip, zip_filename)
            return FileResponse(zip_filename, media_type='application/zip', filename="descarga_EB_y_EA.zip")
        else:
            raise HTTPException(status_code=404, detail="No files generated or requested for download")

