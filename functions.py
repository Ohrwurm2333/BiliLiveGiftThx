from bilibili import bilibili
from configloader import ConfigLoader
import random
from utils import check_room
from statistics import Statistics
import time
import datetime
import asyncio
import printer
import aiohttp
import login
import utils
from sqlapi import db, Live
import rafflehandler
import websockets
import traceback
import struct
import json
import re
import sys
import queue



# async def preprocess_send_danmu_msg_web(msg, roomid):
#     real_roomid = fetch_real_roomid(roomid)
#     json_response = await bilibili.request_send_danmu_msg_web(msg, real_roomid)
#     print(json_response)
