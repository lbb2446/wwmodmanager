#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import os

# Simple 32x32 blue square icon as base64 PNG
ICON_BASE64 = """
iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlz
AAAOxAAADsQBlSsOGwAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAGsSURB
VFiF7ZY9TsNAEIW/WVuFQhFCOgoKGhoKLkBFRcMFKHkCJSfoKDiCOhIKJRL2WmIMPaux13Zi
OxYVefv2e+b/m9m7YIz5L0T9w2Yzs6Isy7IsyxpAHEcBEUVRBEQU RGGMoYUA0ZhzYoylhQDR
mHNiLAUoinJBKaUApJQyF1BK6Yq01pZSKgUppS4ppS4BiqJcUEopAKWUuYCU0pWUUloopSwF
KKUuKKUuAYqiXFBKKQCllLmAlNKVlFKWAJRSlxRSigIopSwBKKUuKKUuAYqiXFBKKQCllLmA
lNKVlFKWAJRSlxRSigIopSwBKKUuKKUuAYqiXFBKKQCllLmAlNKVlFKWAJRSlxRSigIopSwB
KKUuKKUuAYqiXFBKKQCllLmAlNKVlFKWAJRSlxRSigIopSwBKKUuKKUuAYqiXFBKKQCllLmA
lNKVlFKWAJRSlxRSigIopSwBKKUuKKUuAYqiXFBKKQCllLmAlNKVlFKWAJRSlxRSigIopSwB
KKUuKKUuAYqiXFBKKQCllLmAlNKVlFKWAJRSlxRSigIopSwBKKUuKKUuAYqiXFBKKf4BnT6E
k/3z6YoAAAAASUVORK5CYII=
""".strip()

def create_default_icon():
    icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
    if not os.path.exists(icon_path):
        with open(icon_path, 'wb') as f:
            f.write(base64.b64decode(ICON_BASE64))
        print(f"Created default icon: {icon_path}")
    else:
        print(f"Icon already exists: {icon_path}")

if __name__ == '__main__':
    create_default_icon()
