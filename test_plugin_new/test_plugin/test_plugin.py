# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TestPlugin
                                 A QGIS plugin
 Test plugin with layer selection
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2023-11-22
        git sha              : $Format:%H$
        copyright            : (C) 2023 by St. Petersburg State University
        email                : support@gis-ops.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry
import os.path
import requests

import json
import requests
from shapely.geometry import Point, LineString, Polygon, mapping
import geopandas as gpd
from qgis.core import QgsVectorLayer, QgsProject

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .test_plugin_dialog import TestPluginDialog


class TestPlugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'TestPlugin_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Test Plugin')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = True
        self.layer_added = False

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('TestPlugin', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/test_plugin/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Test Plugin'),
                action)
            self.iface.removeToolBarIcon(action)
            
    def run(self):
        if self.first_start == True:
            self.first_start = False
            self.dlg = TestPluginDialog()
            self.dlg.comboBox.addItems(['Санкт-Петербург', 'Москва'])

        self.dlg.show()
        
        result = self.dlg.exec_()
        
        if result:
            overpass_query = """
            [out:json];
            (
            way["building"](poly:"59.971389 30.252778 59.971111 30.262500 59.973333 30.262222 59.973611 30.252500 59.971389 30.252778");
            );
            (._;>;);
            out body;
            """

            overpass_url = "https://overpass-api.de/api/interpreter"
            response = requests.get(overpass_url, params={"data": overpass_query})
            
            if response.status_code == 200:
                data = response.json()
                
                nodes = {node['id']: Point(node['lon'], node['lat']) for node in data['elements'] if node['type'] == 'node'}

                # Создание списка словарей, каждый из которых будет геообъектом
                features = []
                for element in data['elements']:
                    if element['type'] == 'way':
                        points = [nodes[node_id] for node_id in element['nodes']]
                        line = LineString(points)
                        feature = {
                            'type': 'Feature',
                            'properties': {
                                'name': self.dlg.comboBox.currentText()
                                },
                            'geometry': mapping(line)
                        }
                        features.append(feature)

                geojson = {
                    'type': 'FeatureCollection',
                    'features': features,
                }

                gdf = gpd.GeoDataFrame.from_features(geojson)
                layer_name = f"Buildings of {self.dlg.comboBox.currentText()}"
                layer_out = QgsVectorLayer(gdf.to_json(), layer_name, "ogr")

                if not layer_out.isValid():
                    print("Layer failed to load!")
                else:
                    QgsProject.instance().addMapLayer(layer_out)
            else:
                print("Ошибка при запросе к Overpass API:", response.text)

    # def run(self):
    #     """Run method that performs all the real work"""

    #     # Create the dialog with elements (after translation) and keep reference
    #     # Only create GUI ONCE in callback, so that it will only load when the plugin is started
    #     if self.first_start == True:
    #         self.first_start = False
    #         self.dlg = TestPluginDialog()
    #         self.dlg.comboBox.addItems(['Дороги Санкт-Петербурга', 'Здания Санкт-Петербурга'])

    #     # show the dialog
    #     self.dlg.show()
    #     # Run the dialog event loop
    #     result = self.dlg.exec_()

    #     if result:
    #         # Send the Overpass Turbo query
    #         if self.dlg.comboBox.currentIndex() == 1:  # Check if "Здания Санкт-Петербурга" is selected
    #             query = '''
    #             [out:json];
    #             area[name="Санкт-Петербург"]->.a;
    #             way(area.a)["building"];
    #             /*added by auto repair*/
    #             (._;>;);
    #             /*end of auto repair*/
    #             out body;
    #             '''
    #         else:  # Use the existing query for "Дороги Санкт-Петербурга"
    #             query = '''
    #             [out:json];
    #             area[name="Санкт-Петербург"]->.a;
    #             way(area.a)["highway"="primary"];
    #             /*added by auto repair*/
    #             (._;>;);
    #             /*end of auto repair*/
    #             out body;
    #             '''

    #         url = 'https://overpass-api.de/api/interpreter'
    #         data = {
    #             'data': query
    #         }

    #         response = requests.post(url, data=data)

    #         geojson_data = response.json()

    #         if self.dlg.comboBox.currentIndex() == 1:  # Check if "Здания Санкт-Петербурга" is selected
    #             layer_name = "Buildings of Saint Petersburg"
    #         else:
    #             layer_name = "Roads of Saint Petersburg"

    #         geojson_layer = QgsVectorLayer(json.dumps(geojson_data), layer_name, "ogr")

    #         if geojson_layer.isValid():
    #             QgsProject.instance().addMapLayer(geojson_layer)
    #             print("Layer successfully added")
    #             # Zoom to the layer extent
    #             canvas = iface.mapCanvas()
    #             canvas.setExtent(geojson_layer.extent())
    #             canvas.refresh()
    #         else:
    #             print("Error adding layer")

