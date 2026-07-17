# -*- coding: utf-8 -*-
"""Test for ApplicationBootstrap."""

from core.application_bootstrap import ApplicationBootstrap


def test_create():
    svc = ApplicationBootstrap()
    assert svc is not None


def test_build():
    svc = ApplicationBootstrap()
    result = svc.build()
    assert result is not None
    assert result is svc
