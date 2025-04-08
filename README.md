# quadrat-coverage

This package is designed to calculate the percent coverage of vegetation within
certain areas (quadrats). The vegetation information is taken from a single-band
raster image where the pixel values represent the non-dimensional vegetation
index (NDVI).


## Workflow

The workflow for calculating percent coverage is as follows:

1. Clip the input raster to remove unwanted regions, such as trees and ocean.
2. Classify the image into 'vegetation'/'non vegetation' using a threshold.
3. Calculate the percent of vegetation coverage for a grid of quadrats.

The following images illustrate the workflow.
| Description                                                            | Image                                            |
| ---------------------------------------------------------------------- | ------------------------------------------------ |
| RGB image                                                              | <img height=150px src=docs/rgb.jpg>              |
| NDVI image (greyscale)                                                 | <img height=150px src=docs/ndvi-grey.jpg>        |
| NDVI image (pseduocolour) with clipping mask                           | <img height=150px src=docs/ndvi-pseudo-grey.jpg> |
| Classified/binary image after clipping (yellow pixels show vegetation) | <img height=150px src=docs/nvdvi-pseudo-bw.jpg>  |
| Quadrats with percent vegetation coverage                              | <img height=150px src=docs/exactextract.jpg>     |


There are four inputs required for the calculation:

| Name          | Type                             | Description                                   |
| ------------- | -------------------------------- | --------------------------------------------- |
| NDVI image    | raster (e.g. tif)                | Single band input image of vegetated area     |
| Clipping mask | vector (e.g. shapefile, geojson) | Clipping polygon(s)                           |
| Quadrat grid  | vector (e.g. shapefile, geojson) | Quadrat polygons                              |
| Threshold     | Float                            | Threshold value for vegetation classification |


## Threshold value

An appropriate vegetation threshold value can be determined by changing the symbology settings in QGIS.

<!-- ![](docs/interactive-thresholding.gif) -->


|                |                             |                             |                             |
| -------------- | --------------------------: | --------------------------: | --------------------------: |
|                | ![](docs/threshold-0.1.jpg) | ![](docs/threshold-0.3.jpg) | ![](docs/threshold-0.5.jpg) |
| NDVI threshold |                         0.1 |                         0.3 |                         0.5 |



## Installation

This package requires the `exactextract` library, which can be installed using `pip`.

1. Open the `OSGeo4W Shell`.
2. Type the command: `pip install exactextract`

![](docs/osgeo4w-shell.png)

## QGIS plugin



## Command line tool

## Motivation

QGIS already has a tool for calculating zonal statistics. Why is the `exactextract` package needed? QGIS's built in zonal statistics tool `zonalstatisticsfb` does not handle edge cases correctly, where the quadrat polygons include regions beyond the raster extent. 

In the example below, the QGIS zonal statistics tool reports 64% vegetation coverage in the lower left cell, because it is omitting the empty pixels outside the red clipping boundary. This value is clearly incorrect, because the majority of the cell is empty. In contrast, the `exactextract` package allows empty pixels to have a zero value (i.e. 'not vegetation') using the when calculating the percent coverage for the total cell area.


|                                                       |                                               |
| ----------------------------------------------------- | --------------------------------------------- |
| Source: QGIS `zonalstatisticsfb`                      | Source: `exactextract`                        |
| ![](docs/zonal-statistics.jpg)                        | ![](docs/exactextract.jpg)                    |
| Empty pixels are excluded (% cover is overestimated). | Empty pixels are considered 'not vegetation'. |

