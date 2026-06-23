from bokeh.io import curdoc
from bokeh.models import Tabs
from mongodb_explorer import MongoExplorer


def test_explorer():
    explorer = MongoExplorer("mongodb://192.168.30.104:27017", "test", "runconfig")
    assert explorer is not None


def test_explorer_panel():
    explorer = MongoExplorer("mongodb://192.168.30.104:27017", "test", "runconfig")
    assert explorer.panel is not None


def test_explorer_in_app():
    explorer1 = MongoExplorer("mongodb://192.168.30.104:27017", "test", "runconfig")
    explorer2 = MongoExplorer("mongodb://192.168.30.104:27017", "test", "runconfig")

    tabs = Tabs(tabs=[explorer1.panel, explorer2.panel], sizing_mode="stretch_both")

    curdoc().add_root(tabs)
    assert len(curdoc().roots) == 1
