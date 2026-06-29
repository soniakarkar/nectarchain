from bokeh.io import curdoc
from bokeh.models import Div, TabPanel, Tabs
from mongodb_explorer import MongoExplorer

# Set the MongoDB connection details for testing
MongoURL = "mongodb://192.168.30.104:27017"
collection = "test"
database = "runconfig"

explorer = MongoExplorer(MongoURL, collection, database)
another_tab = TabPanel(title="Another Tab", child=Div(text="Here will be dqm tabs"))
tabs = Tabs(tabs=[another_tab, explorer.panel], sizing_mode="stretch_both")
curdoc().add_root(tabs)
