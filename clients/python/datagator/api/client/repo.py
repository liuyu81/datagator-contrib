# -*- coding: utf-8 -*-
"""
    datagator.api.client.repo
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2015 by `University of Denver <http://pardee.du.edu/>`_
    :license: Apache 2.0, see LICENSE for more details.

    :author: `LIU Yu <liuyu@opencps.net>`_
    :date: 2015/01/28
"""

from __future__ import unicode_literals, with_statement

import jsonschema

from . import environ
from ._compat import to_native, to_unicode
from ._entity import Entity


__all__ = ['DataSet', 'Repo', ]
__all__ = [to_native(n) for n in __all__]


class DataSet(Entity):

    __slots__ = ['__name', '__repo', ]

    def __init__(self, name, repo):
        super(DataSet, self).__init__(self.__class__.__name__)
        self.__name = to_unicode(name)
        self.__repo = repo
        try:
            self.schema.validate(self.id)
        except jsonschema.ValidationError:
            raise AssertionError("invalid dataset name")
        pass

    @property
    def uri(self):
        return "{0}/{1}".format(self.repo.name, self.name)

    @property
    def id(self):
        return dict([
            ("kind", "datagator#DataSet"),
            ("name", self.name),
            ("repo", self.repo.id),
        ])

    @property
    def name(self):
        return self.__name

    @property
    def repo(self):
        return self.__repo

    @property
    def rev(self):
        content = self.cache
        if "rev" not in content:
            self.cache = None
            content = self.cache
        return content.get("rev", 0)

    def __iter__(self):
        for item in self.cache.get("items", []):
            yield item.get("name")
        pass

    def __len__(self):
        return self.cache.get("itemsCount", 0)

    pass


class Repo(Entity):

    __slots__ = ['__name', ]

    def __init__(self, name, credentials=None):
        super(Repo, self).__init__(self.__class__.__name__)
        self.__name = to_unicode(name)
        if credentials is not None:
            self.service.auth = (self.name, credentials)
        pass

    @property
    def uri(self):
        return self.name

    @property
    def name(self):
        return self.__name

    @property
    def id(self):
        return dict([
            ("kind", "datagator#Repo"),
            ("name", self.name),
        ])

    def __contains__(self, dsname):
        try:
            # if `dsname` is not a valid name for a DataSet entity, then it is
            # guaranteed to *not* exist in the storage backend.
            ds = DataSet(dsname, self)
            # looking up `Entity.__cache__` is more preferrable than `ds.cache`
            # because the latter may trigger connection to the backend service
            if Entity.__cache__.exists(ds.uri):
                return True
            return ds.cache is not None
        except (AssertionError, ):
            return False
        return False  # should NOT reach here

    def __getitem__(self, dsname):
        try:
            if dsname in self:
                return DataSet(dsname, self)
        except (AssertionError, ):
            pass
        raise KeyError("invalid dataset")

    def __setitem__(self, dsname, dataset):
        target = DataSet(dsname, self)
        if isinstance(dataset, (dict, list, tuple)):
            # inspect and serialize content
            pass
        elif not isinstance(dataset, DataSet):
            raise ValueError("invalid dataset")
        elif dataset.uri != target.uri:
            raise ValueError("inconsistent dataset")
        # create / update dataset
        response = self.service.put(target.uri, target.id)
        if response.status_code not in (200, 201):
            # response body should be a valid JSON object
            if response.headers['Content-Type'] != "application/json":
                raise RuntimeError("invalid response from backend service")
            # response should pass schema validation
            data = response.json()
            self.schema.validate(data)
            msg = "failed to create entity in backend service"
            if data.get("kind") == "datagator#Error":
                msg = "{0} ({1}): {2}".format(
                    msg, data.get("code", "N/A"), data.get("message", ""))
                raise RuntimeError(msg)
        else:
            # invalidate local cache
            target.cache = None
            self.cache = None
        # TODO: commit content
        pass

    def __delitem__(self, dsname):
        raise NotImplementedError()

    def __iter__(self):
        for ds in self.cache.get("items", []):
            yield ds.get("name")
        pass

    def __len__(self):
        return self.cache.get("itemsCount", 0)

    pass
