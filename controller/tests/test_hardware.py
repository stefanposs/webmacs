"""Tests for hardware interface."""

from webmacs_controller.services.hardware import MockHardware


def test_mock_hardware_read_returns_float(mock_hardware: MockHardware) -> None:
    value = mock_hardware.read_value("pt100_1", "temperature")
    assert isinstance(value, float)


def test_mock_hardware_write_does_not_raise(mock_hardware: MockHardware) -> None:
    mock_hardware.write_value("valve1", "1.0")


def test_mock_hardware_read_different_types() -> None:
    hw = MockHardware()
    temp = hw.read_value("pt100_1", "temperature")
    pressure = hw.read_value("pressure_1", "pressure")
    assert 0 <= temp <= 500
    assert 0 <= pressure <= 10
