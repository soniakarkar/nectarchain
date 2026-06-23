from bokeh.io import curdoc
from bokeh.models import Tabs
from nectarchain.dqm.bokeh_app.mongodb_explorer import MongoExplorer

explorer1 = MongoExplorer("mongodb://192.168.30.104:27017", "test", "runconfig")
explorer2 = MongoExplorer("mongodb://192.168.30.104:27017", "test", "runconfig")

tabs = Tabs(tabs=[explorer1.panel, explorer2.panel])
curdoc().add_root(tabs)