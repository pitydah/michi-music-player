# -*- coding: utf-8 -*-
"""Test for ConfirmationService."""

from core.confirmation_service import ConfirmationService


def test_create():
    svc = ConfirmationService()
    assert svc is not None


def test_request_and_approve():
    svc = ConfirmationService()
    req = svc.request("op1", "target1", description="test")
    assert req is not None
    approved = svc.approve(req.token)
    assert approved is not None
    assert approved.approved is True
