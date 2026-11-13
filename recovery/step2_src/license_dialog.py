"""BMW license dialog — editable reimplementation of recovered UI contract.

Reconstructed from license_dialog.pyc structure (PySide6, asynchronous
worker, QSettings). Not the original GUI source and not integrated into
protected bmw_gui.pyc. It calls the server; it does not bypass validation.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from PySide6.QtCore import Qt, QThread, Signal, QSettings
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QProgressBar,
)

from license_client import check_license, resolve_license_url


def _mask_key(key: str) -> str:
    value = str(key or "").strip()
    if len(value) <= 6:
        return "*" * len(value)
    return value[:3] + "*" * (len(value) - 6) + value[-3:]


def persist_license_response(key: str, machine: str, left: int | None, message: str, raw: dict[str, Any]) -> None:
    """Store server-returned metadata, not an invented or forced activation."""
    settings = QSettings("BMW", "BMWApp")
    settings.setValue("license/masked_key", _mask_key(key))
    settings.setValue("license/machine_id", machine)
    settings.setValue("license/left_days", left if left is not None else "")
    settings.setValue("license/server_msg", message)
    settings.setValue("license/app_version", str(raw.get("appVersion") or raw.get("version") or ""))
    settings.setValue("license/key_type", str(raw.get("KeyType") or ""))
    settings.setValue("license/paid", str(raw.get("paid") or ""))
    settings.setValue("license/update_url", str(raw.get("UpdateURL") or ""))
    settings.setValue("license/tokens", json.dumps(raw.get("tokens") or {}))
    settings.setValue("license/fauth_raw", json.dumps(raw))
    settings.sync()


class LicenseCheckWorker(QThread):
    finished_check = Signal(bool, object, str)
    errored = Signal(str)

    def __init__(self, api_url: str, license_key: str, device_id: str, parent: Any = None):
        super().__init__(parent)
        self.api_url = api_url
        self.license_key = license_key
        self.device_id = device_id

    def run(self) -> None:
        try:
            ok, left, mode, msg, raw = check_license(
                self.api_url, self.license_key, self.device_id
            )
            self.finished_check.emit(ok, {"leftDays": left, "mode": mode, "raw": raw}, msg)
        except Exception as exc:
            self.errored.emit("License verification could not be completed.")


class LicenseDialog(QDialog):
    """Standalone dialog for a rebuilt app. Requires original device-ID getter."""

    def __init__(
        self,
        device_id_provider: Callable[[], str],
        *,
        api_url: str | None = None,
        preload_key: str = "",
        parent: Any = None,
    ):
        super().__init__(parent)
        self._api_url = api_url or resolve_license_url()
        self._device_id = device_id_provider()
        self.verified = False
        self.license_key = ""
        self.left_days: int | None = None
        self.mode = ""
        self.server_message = ""
        self.worker: LicenseCheckWorker | None = None
        self.setWindowTitle("License Verification")
        self.setModal(True)
        self.setFixedSize(420, 255)
        self._build_ui(preload_key)

    def _build_ui(self, preload_key: str) -> None:
        root = QVBoxLayout(self)
        title = QLabel("<b>Enter your license key to continue</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Enter license key")
        self.inp.setText(preload_key)
        root.addWidget(self.inp)
        dev = QLabel("Device ID: " + self._device_id)
        dev.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(dev)
        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        root.addWidget(self.msg)
        self.loader = QProgressBar()
        self.loader.setRange(0, 0)
        self.loader.setVisible(False)
        root.addWidget(self.loader)
        actions = QHBoxLayout()
        self.btn = QPushButton("Verify")
        self.btn.clicked.connect(self._on_verify_clicked)
        actions.addWidget(self.btn)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)
        root.addLayout(actions)

    def _on_verify_clicked(self) -> None:
        key = self.inp.text().strip()
        if not key:
            self._set_message("Please enter license key.", True)
            return
        self._set_busy(True)
        self._set_message("Checking license…", False)
        self.worker = LicenseCheckWorker(self._api_url, key, self._device_id, self)
        self.worker.finished_check.connect(self._on_finished)
        self.worker.errored.connect(self._on_error)
        self.worker.start()

    def _on_finished(self, ok: bool, payload: Any, message: str) -> None:
        self._set_busy(False)
        if not ok:
            self._set_message(message or "License check failed.", True)
            return
        self.verified = True
        self.license_key = self.inp.text().strip()
        self.left_days = payload.get("leftDays")
        self.mode = payload.get("mode") or ""
        self.server_message = message
        persist_license_response(self.license_key, self._device_id, self.left_days, message, payload.get("raw") or {})
        self.accept()

    def _on_error(self, error: str) -> None:
        self._set_busy(False)
        self._set_message(error, True)

    def _set_busy(self, busy: bool) -> None:
        self.loader.setVisible(busy)
        self.btn.setEnabled(not busy)
        self.inp.setEnabled(not busy)

    def _set_message(self, message: str, error: bool) -> None:
        self.msg.setText(message)
        self.msg.setStyleSheet("color: #d35c5c;" if error else "")
