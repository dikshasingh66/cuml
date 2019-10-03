# Copyright (c) 2019, NVIDIA CORPORATION.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import pytest
import cudf
import numpy as np
import pandas as pd

from cuml import Lasso as cuLasso
from cuml.linear_model import ElasticNet as cuElasticNet
from cuml.test.utils import small_regression_dataset

from sklearn.linear_model import Lasso
from sklearn.linear_model import ElasticNet
from sklearn.datasets import make_regression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split


def unit_param(*args, **kwargs):
    return pytest.param(*args, **kwargs, marks=pytest.mark.unit)


def quality_param(*args, **kwargs):
    return pytest.param(*args, **kwargs, marks=pytest.mark.quality)


def stress_param(*args, **kwargs):
    return pytest.param(*args, **kwargs, marks=pytest.mark.stress)


@pytest.mark.parametrize('datatype', [np.float32, np.float64])
@pytest.mark.parametrize('X_type', ['ndarray'])
@pytest.mark.parametrize('alpha', [0.1, 0.001])
@pytest.mark.parametrize('algorithm', ['cyclic', 'random'])
@pytest.mark.parametrize('nrows', [unit_param(20), quality_param(5000),
                         stress_param(500000)])
@pytest.mark.parametrize('ncols', [unit_param(3), quality_param(100),
                         stress_param(1000)])
@pytest.mark.parametrize('n_info', [unit_param(2), quality_param(50),
                         stress_param(500)])
def test_lasso(datatype, X_type, alpha, algorithm,
               nrows, ncols, n_info):

    X, y = make_regression(n_samples=nrows, n_features=ncols,
                           n_informative=n_info, random_state=0)
    X = X.astype(datatype)
    y = y.astype(datatype)
    X_train, X_test, y_train, y_test = train_test_split(X, y, train_size=0.8)
    cu_lasso = cuLasso(alpha=np.array([alpha]), fit_intercept=True,
                       normalize=False, max_iter=1000,
                       selection=algorithm, tol=1e-10)

    if X_type == 'dataframe':
        y_train = pd.DataFrame({'fea0': y_train[0:, ]})
        X_train = pd.DataFrame(
            {'fea%d' % i: X_train[0:, i] for i in range(X_train.shape[1])})
        X_test = pd.DataFrame(
            {'fea%d' % i: X_test[0:, i] for i in range(X_test.shape[1])})
        X_cudf = cudf.DataFrame.from_pandas(X_train)
        X_cudf_test = cudf.DataFrame.from_pandas(X_test)
        y_cudf = y_train.values
        y_cudf = y_cudf[:, 0]
        y_cudf = cudf.Series(y_cudf)
        cu_lasso.fit(X_cudf, y_cudf)
        cu_predict = cu_lasso.predict(X_cudf_test)

    elif X_type == 'ndarray':

        cu_lasso.fit(X_train, y_train)
        cu_predict = cu_lasso.predict(X_test)

    cu_r2 = r2_score(y_test, cu_predict)

    if nrows < 500000:
        sk_lasso = Lasso(alpha=np.array([alpha]), fit_intercept=True,
                         normalize=False, max_iter=1000,
                         selection=algorithm, tol=1e-10)
        sk_lasso.fit(X_train, y_train)
        sk_predict = sk_lasso.predict(X_test)
        sk_r2 = r2_score(y_test, sk_predict)
        assert cu_r2 >= sk_r2 - 0.07


@pytest.mark.parametrize('datatype', [np.float32, np.float64])
@pytest.mark.parametrize('X_type', ['ndarray'])
def test_lasso_default(datatype, X_type):
    X_train, X_test, y_train, y_test = small_regression_dataset(datatype)

    cu_lasso = cuLasso()

    cu_lasso.fit(X_train, y_train)
    cu_predict = cu_lasso.predict(X_test)
    cu_r2 = r2_score(y_test, cu_predict)

    sk_lasso = Lasso()
    sk_lasso.fit(X_train, y_train)
    sk_predict = sk_lasso.predict(X_test)
    sk_r2 = r2_score(y_test, sk_predict)
    assert cu_r2 >= sk_r2 - 0.07


@pytest.mark.parametrize('datatype', [np.float32, np.float64])
@pytest.mark.parametrize('X_type', ['ndarray'])
@pytest.mark.parametrize('alpha', [0.2, 0.7])
@pytest.mark.parametrize('algorithm', ['cyclic', 'random'])
@pytest.mark.parametrize('nrows', [unit_param(20), quality_param(5000),
                         stress_param(500000)])
@pytest.mark.parametrize('ncols', [unit_param(3), quality_param(100),
                         stress_param(1000)])
@pytest.mark.parametrize('n_info', [unit_param(2), quality_param(50),
                         stress_param(500)])
def test_elastic_net(datatype, X_type, alpha, algorithm,
                     nrows, ncols, n_info):

    X, y = make_regression(n_samples=nrows, n_features=ncols,
                           n_informative=n_info, random_state=0)

    X_train, X_test, y_train, y_test = train_test_split(X, y, train_size=0.8)

    elastic_cu = cuElasticNet(alpha=np.array([alpha]), fit_intercept=True,
                              normalize=False, max_iter=1000,
                              selection=algorithm, tol=1e-10)

    if X_type == 'dataframe':
        y_train = pd.DataFrame({'fea0': y_train[0:, ]})
        X_train = pd.DataFrame(
            {'fea%d' % i: X_train[0:, i] for i in range(X_train.shape[1])})
        X_test = pd.DataFrame(
            {'fea%d' % i: X_test[0:, i] for i in range(X_test.shape[1])})
        X_cudf = cudf.DataFrame.from_pandas(X_train)
        X_cudf_test = cudf.DataFrame.from_pandas(X_test)
        y_cudf = y_train.values
        y_cudf = y_cudf[:, 0]
        y_cudf = cudf.Series(y_cudf)
        elastic_cu.fit(X_cudf, y_cudf)
        cu_predict = elastic_cu.predict(X_cudf_test)

    elif X_type == 'ndarray':

        elastic_cu.fit(X_train, y_train)
        cu_predict = elastic_cu.predict(X_test)

    cu_r2 = r2_score(y_test, cu_predict)

    if nrows < 500000:
        elastic_sk = ElasticNet(alpha=np.array([alpha]), fit_intercept=True,
                                normalize=False, max_iter=1000,
                                selection=algorithm, tol=1e-10)
        elastic_sk.fit(X_train, y_train)
        sk_predict = elastic_sk.predict(X_test)
        sk_r2 = r2_score(y_test, sk_predict)

        assert cu_r2 >= sk_r2 - 0.07


@pytest.mark.parametrize('datatype', [np.float32, np.float64])
@pytest.mark.parametrize('X_type', ['ndarray'])
def test_elastic_net_default(datatype, X_type):

    X_train, X_test, y_train, y_test = small_regression_dataset(datatype)

    elastic_cu = cuElasticNet()
    elastic_cu.fit(X_train, y_train)
    cu_predict = elastic_cu.predict(X_test)
    cu_r2 = r2_score(y_test, cu_predict)

    elastic_sk = ElasticNet()
    elastic_sk.fit(X_train, y_train)
    sk_predict = elastic_sk.predict(X_test)
    sk_r2 = r2_score(y_test, sk_predict)
    assert cu_r2 >= sk_r2 - 0.07
