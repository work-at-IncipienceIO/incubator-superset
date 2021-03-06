# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from datetime import datetime

import numpy as np
import pandas as pd

from superset.dataframe import df_to_records
from superset.db_engine_specs import BaseEngineSpec
from superset.result_set import dedup, SupersetResultSet

from .base_tests import SupersetTestCase


class SupersetResultSetTestCase(SupersetTestCase):
    def test_dedup(self):
        self.assertEqual(dedup(["foo", "bar"]), ["foo", "bar"])
        self.assertEqual(
            dedup(["foo", "bar", "foo", "bar", "Foo"]),
            ["foo", "bar", "foo__1", "bar__1", "Foo"],
        )
        self.assertEqual(
            dedup(["foo", "bar", "bar", "bar", "Bar"]),
            ["foo", "bar", "bar__1", "bar__2", "Bar"],
        )
        self.assertEqual(
            dedup(["foo", "bar", "bar", "bar", "Bar"], case_sensitive=False),
            ["foo", "bar", "bar__1", "bar__2", "Bar__3"],
        )

    def test_get_columns_basic(self):
        data = [("a1", "b1", "c1"), ("a2", "b2", "c2")]
        cursor_descr = (("a", "string"), ("b", "string"), ("c", "string"))
        results = SupersetResultSet(data, cursor_descr, BaseEngineSpec)
        self.assertEqual(
            results.columns,
            [
                {"is_date": False, "type": "STRING", "name": "a"},
                {"is_date": False, "type": "STRING", "name": "b"},
                {"is_date": False, "type": "STRING", "name": "c"},
            ],
        )

    def test_get_columns_with_int(self):
        data = [("a1", 1), ("a2", 2)]
        cursor_descr = (("a", "string"), ("b", "int"))
        results = SupersetResultSet(data, cursor_descr, BaseEngineSpec)
        self.assertEqual(
            results.columns,
            [
                {"is_date": False, "type": "STRING", "name": "a"},
                {"is_date": False, "type": "INT", "name": "b"},
            ],
        )

    def test_get_columns_type_inference(self):
        data = [
            (1.2, 1, "foo", datetime(2018, 10, 19, 23, 39, 16, 660000), True),
            (3.14, 2, "bar", datetime(2019, 10, 19, 23, 39, 16, 660000), False),
        ]
        cursor_descr = (("a", None), ("b", None), ("c", None), ("d", None), ("e", None))
        results = SupersetResultSet(data, cursor_descr, BaseEngineSpec)
        self.assertEqual(
            results.columns,
            [
                {"is_date": False, "type": "FLOAT", "name": "a"},
                {"is_date": False, "type": "INT", "name": "b"},
                {"is_date": False, "type": "STRING", "name": "c"},
                {"is_date": True, "type": "DATETIME", "name": "d"},
                {"is_date": False, "type": "BOOL", "name": "e"},
            ],
        )

    def test_is_date(self):
        is_date = SupersetResultSet.is_date
        self.assertEqual(is_date("DATETIME"), True)
        self.assertEqual(is_date("TIMESTAMP"), True)
        self.assertEqual(is_date("STRING"), False)
        self.assertEqual(is_date(""), False)
        self.assertEqual(is_date(None), False)

    def test_dedup_with_data(self):
        data = [("a", 1), ("a", 2)]
        cursor_descr = (("a", "string"), ("a", "string"))
        results = SupersetResultSet(data, cursor_descr, BaseEngineSpec)
        column_names = [col["name"] for col in results.columns]
        self.assertListEqual(column_names, ["a", "a__1"])

    def test_int64_with_missing_data(self):
        data = [(None,), (1239162456494753670,), (None,), (None,), (None,), (None,)]
        cursor_descr = [("user_id", "bigint", None, None, None, None, True)]
        results = SupersetResultSet(data, cursor_descr, BaseEngineSpec)
        self.assertEqual(results.columns[0]["type"], "BIGINT")

    def test_nullable_bool(self):
        data = [(None,), (True,), (None,), (None,), (None,), (None,)]
        cursor_descr = [("is_test", "bool", None, None, None, None, True)]
        results = SupersetResultSet(data, cursor_descr, BaseEngineSpec)
        self.assertEqual(results.columns[0]["type"], "BOOL")
        df = results.to_pandas_df()
        self.assertEqual(
            df_to_records(df),
            [
                {"is_test": None},
                {"is_test": True},
                {"is_test": None},
                {"is_test": None},
                {"is_test": None},
                {"is_test": None},
            ],
        )

    def test_empty_datetime(self):
        data = [(None,)]
        cursor_descr = [("ds", "timestamp", None, None, None, None, True)]
        results = SupersetResultSet(data, cursor_descr, BaseEngineSpec)
        self.assertEqual(results.columns[0]["type"], "TIMESTAMP")

    def test_no_type_coercion(self):
        data = [("a", 1), ("b", 2)]
        cursor_descr = [
            ("one", "varchar", None, None, None, None, True),
            ("two", "int", None, None, None, None, True),
        ]
        results = SupersetResultSet(data, cursor_descr, BaseEngineSpec)
        self.assertEqual(results.columns[0]["type"], "VARCHAR")
        self.assertEqual(results.columns[1]["type"], "INT")

    def test_empty_data(self):
        data = []
        cursor_descr = [
            ("emptyone", "varchar", None, None, None, None, True),
            ("emptytwo", "int", None, None, None, None, True),
        ]
        results = SupersetResultSet(data, cursor_descr, BaseEngineSpec)
        self.assertEqual(results.columns, [])
