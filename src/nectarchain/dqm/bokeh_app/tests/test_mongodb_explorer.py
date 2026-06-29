# import unittest.mock
import pymongo
import pytest
from bokeh.io import curdoc
from bokeh.models import Div, TabPanel, Tabs

from nectarchain.dqm.bokeh_app.mongodb_explorer import MongoExplorer, _infer_fields

# from pytest_mock_resources import create_mongo_fixture
# NumericRangeControl,; _build_query,; _make_columns,; _make_control,

# Set to True to enable manual testing with a real MongoDB connection
manualtest = False
# Set the MongoDB connection details for testing
MongoURL = "mongodb://192.168.30.104:27017"
collection_name = "test"
database_name = "runconfig"


@pytest.fixture(scope="module")
def mock_collection():
    # Create a mock MongoDB collection with sample documents
    # mock_col = pymongo.collection.Collection(
    # pymongo.MongoClient(MongoURL)[database_name], collection_name
    # )
    return [
        {"name": "Alice", "age": 30, "city": "New York"},
        {"name": "Bob", "age": 25, "city": "Los Angeles"},
        {"name": "Charlie", "age": 35, "city": "Chicago"},
    ]


def test_infer_fields(mock_collection):
    # Call the _infer_fields method
    inferred_fields = _infer_fields(mock_collection)
    # Assert that the inferred fields match the expected fields
    expected_fields = ["name", "age", "city"]
    assert set(inferred_fields) == set(expected_fields)


@pytest.fixture(scope="module")
def mongo_explorer():
    explorer = MongoExplorer(MongoURL, collection_name, database_name)
    return explorer


@pytest.mark.skipif(
    manualtest is False, reason="MongoDB connection required for this test"
)
def test_mongo_explorer_initialization(mongo_explorer):
    explorer = MongoExplorer(MongoURL, collection_name, database_name)
    assert isinstance(explorer, MongoExplorer)
    assert isinstance(explorer._client, pymongo.MongoClient)
    assert explorer.coll_name == collection_name
    assert explorer.db_name == database_name


@pytest.mark.skipif(
    manualtest is False, reason="MongoDB connection required for this test"
)
def test_explorer_panel(mongo_explorer):
    assert isinstance(mongo_explorer.panel, Tabs)


@pytest.mark.skipif(
    manualtest is False, reason="MongoDB connection required for this test"
)
def test_explorer_in_app(
    mongo_explorer,
):
    another_tab = TabPanel(title="Another Tab", child=Div(text="This is another tab"))
    tabs = Tabs(tabs=[mongo_explorer.panel, another_tab], sizing_mode="stretch_both")
    curdoc().add_root(tabs)
    assert len(curdoc().roots) == 1
