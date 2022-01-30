# -*- coding: utf-8 -*-
import pytest
from src.example.create_order import OrderDirector

director = OrderDirector()
director.construct_order("milk", 3, "SELF_MADE", g_tin= "1241415235")
order = director.order
order.create_order()
print(order.orderId)
print(order)