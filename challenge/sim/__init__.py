"""Simulator package — pure-python tank simulator for offline mission testing.

Layering rule: nothing under `challenge/sim/` may import anything from
`Code/Server/*`. All hardware-facing code lives behind `challenge.hardware`.
"""
