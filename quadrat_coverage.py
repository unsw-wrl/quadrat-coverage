r"""quadrat_coverage.py

Calculate percent coverage of quadrats based on a binary raster.


Usage:

    python quadrat_coverage.py INPUT_FILE


Where INPUT_FILE is an .ini file formatted like this:

    ===> inputs.ini <===
    [site-1]
    raster_ndvi = C:\swc\quadrat-coverage\data\demo_ndvi.tif
    vector_grid = C:\swc\quadrat-coverage\data\demo_grid.geojson
    vector_clip = C:\swc\quadrat-coverage\data\demo_clip.geojson
    vector_output = C:\swc\quadrat-coverage\data\output.geojson
    threshold = 0.3

    [site-2]
    raster_ndvi = ...
    vector_grid = ...
    vector_clip = ...
    vector_output = ...
    threshold = ...


And the input values are:
    'raster_ndvi' : full path to input NDVI raster image
    'vector_grid' : full path to input file containing quadrat polygons
    'vector_clip' : full path to input file containing clipping polygon
    'vector_output' : full path to output vector file where with pc coverage
    'threshold' : threshold value for NDVI vegetation classification


d.howe@wrl.unsw.edu.au
2025-04-07
"""

import exactextract
from osgeo import gdal
import configparser
import sys
import os

# Suppress GDAL FutureWarning
gdal.UseExceptions()

# Accept .ini file as a command-line argument
if len(sys.argv) != 2:
    print("Usage: python quadrat_coverage.py INPUT_FILE")
    sys.exit(1)

input_file = sys.argv[1]


def raster_to_binary(raster_path, threshold):
    raster_ds = gdal.Open(raster_path)
    raster_band = raster_ds.GetRasterBand(1)

    driver = gdal.GetDriverByName("GTiff")
    binary_raster = driver.Create(
        "/vsimem/binary.tif",
        raster_band.XSize,
        raster_band.YSize,
        1,
        gdal.GDT_Byte,
    )
    binary_raster.SetGeoTransform(raster_ds.GetGeoTransform())
    binary_raster.SetProjection(raster_ds.GetProjection())

    raster_data = raster_band.ReadAsArray()
    binary_data = (raster_data > threshold).astype("uint8")

    binary_raster.GetRasterBand(1).WriteArray(binary_data)
    binary_raster.FlushCache()

    return binary_raster


# Clip raster using the vector layer
def clip_raster(raster, vector_path):
    clipped_raster = gdal.Warp(
        "",  # Empty string for in-memory dataset
        raster,
        format="MEM",  # Use the MEM driver for in-memory output
        cutlineDSName=vector_path,
        cropToCutline=True,  # Crop the raster to the clipping extent
        dstNodata=0  # Set NoData value for areas outside the clipping mask
    )
    return clipped_raster


# Read configuration from .ini file
config = configparser.ConfigParser()
config.read(input_file)

for section in config.sections():
    print(f"Processing site: {section}")
    raster_ndvi = config[section]["raster_ndvi"]
    threshold = float(config[section]["threshold"])
    vector_grid = config[section]["vector_grid"]
    vector_clip = config[section]["vector_clip"]
    vector_output = config[section]["vector_output"]

    # Apply NDVI threshold
    binary_raster = raster_to_binary(raster_ndvi, threshold)

    # Clip binary raster
    clipped_raster = clip_raster(binary_raster, vector_clip)

    # Ensure the output file is not open or already exists
    if os.path.exists(vector_output):
        os.remove(vector_output)

    # Infer driver from output file
    ext = os.path.splitext(vector_output)[-1]
    if ext == ".shp":
        driver = "ESRI Shapefile"
    elif ext == ".geojson":
        driver = "geojson"
    else:
        msg = "File format of 'vector_output' must be '.shp' or '.geojson'."
        raise ValueError(msg)

    results = exactextract.exact_extract(rast=clipped_raster,
                                         vec=vector_grid,
                                         ops=["mean(default_value=0)"],
                                         include_geom=True,
                                         output="gdal",
                                         output_options={
                                             "driver": driver,
                                             "filename": vector_output
                                         })
print(f"Processing complete.")
