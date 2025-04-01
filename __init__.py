import os
import json
import tempfile
from PyQt5.QtWidgets import (QAction, QMessageBox, QDialog, QVBoxLayout,
                             QComboBox, QPushButton, QFormLayout, QLineEdit,
                             QApplication)
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsProject
from PyQt5.QtGui import QIcon
from qgis import processing
import exactextract  # pip install exactextract


def classFactory(iface):
    return MinimalPlugin(iface)


class LayerSelectionDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quadrat coverage calculator")
        self.layout = QVBoxLayout()

        self.form_layout = QFormLayout()
        self.vector_combo = QComboBox()
        self.raster_combo = QComboBox()
        self.clip_combo = QComboBox()
        self.threshold_input = QLineEdit()
        self.threshold_input.setPlaceholderText("NDVI threshold")

        self.populate_layers()

        self.form_layout.addRow("Vector layer (quadrats):", self.vector_combo)
        self.form_layout.addRow("Raster layer (NDVI):", self.raster_combo)
        self.form_layout.addRow("Clipping layer:", self.clip_combo)
        self.form_layout.addRow("Threshold:", self.threshold_input)

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.accept)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.run_button)
        self.setLayout(self.layout)

    def populate_layers(self):
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):
                self.vector_combo.addItem(layer.name(), layer)
                self.clip_combo.addItem(layer.name(), layer)
            elif isinstance(layer, QgsRasterLayer):
                self.raster_combo.addItem(layer.name(), layer)

    def selected_vector_layer(self):
        return self.vector_combo.currentData()

    def selected_raster_layer(self):
        return self.raster_combo.currentData()

    def selected_clip_layer(self):
        return self.clip_combo.currentData()

    def threshold_value(self):
        """
        Get the threshold value entered by the user.
        :return: Threshold value as a float or None if not provided.
        """
        try:
            return float(self.threshold_input.text()
                         ) if self.threshold_input.text() else None
        except ValueError:
            return None


class MinimalPlugin:

    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        here = os.path.dirname(__file__)
        icon = QIcon(os.path.join(here, 'assets', 'icon.svg'))
        self.action = QAction(icon, '<b>Quadrat coverage</b>',
                              self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def compute_zonal_statistics(self,
                                 vector_layer: QgsVectorLayer,
                                 raster_layer: QgsRasterLayer,
                                 stat: str,
                                 threshold: float = None,
                                 clip_layer: QgsVectorLayer = None):
        """
        Compute zonal statistics using exactextract with the 'include_geom=True' option.

        :param vector_layer: QgsVectorLayer representing the zones.
        :param raster_layer: QgsRasterLayer representing the raster data.
        :param stat: Statistic to compute (e.g., 'mean', 'sum').
        :param threshold: Threshold value to create a binary raster (optional).
        :param clip_layer: QgsVectorLayer to clip the raster (optional).
        :return: QgsVectorLayer representing the result.
        """
        if clip_layer:
            # Clip the raster using the vector layer
            clipped_raster_path = tempfile.NamedTemporaryFile(
                delete=False, suffix=".tif").name
            processing.run(
                "gdal:cliprasterbymasklayer", {
                    'INPUT': raster_layer.source(),
                    'MASK': clip_layer.source(),
                    'OUTPUT': clipped_raster_path,
                    'CROP_TO_CUTLINE': True,
                    'KEEP_RESOLUTION': True
                })
            raster_layer = QgsRasterLayer(clipped_raster_path,
                                          "Clipped Raster")

        if threshold is not None:
            # Create a binary raster using the threshold with the processing framework
            binary_raster_path = tempfile.NamedTemporaryFile(
                delete=False, suffix=".tif").name
            processing.run(
                "gdal:rastercalculator",
                {
                    'INPUT_A': raster_layer.source(),
                    'BAND_A': 1,
                    'FORMULA': f"A > {threshold}",
                    'OUTPUT': binary_raster_path,
                    'RTYPE': 5  # Byte type for binary raster
                })
            raster_source = binary_raster_path
        else:
            raster_source = raster_layer.source()

        geojson_result = exactextract.exact_extract(raster_source,
                                                    vector_layer.source(),
                                                    [stat],
                                                    include_geom=True)

        # Convert the GeoJSON-like result to a valid GeoJSON string
        geojson_string = json.dumps({
            "type": "FeatureCollection",
            "features": geojson_result
        })

        # Write the GeoJSON string to a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False,
                                                suffix=".geojson")
        temp_file.write(geojson_string.encode('utf-8'))
        temp_file.close()

        # Load the temporary file as a vector layer
        result_layer = QgsVectorLayer(temp_file.name, "Quadrat Coverage",
                                      "ogr")
        if not result_layer.isValid():
            raise RuntimeError(
                "Failed to create memory layer from the result.")

        # Set the CRS of the result layer to match the input vector layer
        result_layer.setCrs(vector_layer.crs())

        # Add the memory layer to the QGIS project
        QgsProject.instance().addMapLayer(result_layer)
        return result_layer

    def run(self):
        dialog = LayerSelectionDialog()
        if dialog.exec_():
            vector_layer = dialog.selected_vector_layer()
            raster_layer = dialog.selected_raster_layer()
            clip_layer = dialog.selected_clip_layer()
            threshold = dialog.threshold_value()
            if vector_layer and raster_layer:
                # Show a message in the status bar
                self.iface.mainWindow().statusBar().showMessage(
                    "Running Quadrat Coverage Plugin...")
                QApplication.processEvents()  # Ensure the message is displayed

                try:
                    result_layer = self.compute_zonal_statistics(
                        vector_layer,
                        raster_layer,
                        'mean(default_value=0)',
                        threshold=threshold,
                        clip_layer=clip_layer)
                    QMessageBox.information(
                        None, 'Zonal Statistics',
                        f'Result layer added: {result_layer.name()}')
                except RuntimeError as e:
                    QMessageBox.critical(None, 'Error', str(e))
                finally:
                    # Clear the status bar message
                    self.iface.mainWindow().statusBar().clearMessage()
            else:
                QMessageBox.warning(
                    None, 'Error',
                    'Please select both a vector and raster layer.')
