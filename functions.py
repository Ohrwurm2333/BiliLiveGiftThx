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
from giftthx import DanMuraffle, DanMuMsgHandle


async def preprocess_send_danmu_msg_web(msg, roomid):
    real_roomid = fetch_real_roomid(roomid)
    json_response = await bilibili.request_send_danmu_msg_web(msg, real_roomid)
    print(json_response)

async def get_listen_room():
    roomid = ConfigLoader().dic_user['other_control']['default_monitor_roomid']
    roomid = await check_room(roomid)
    area_id = await asyncio.shield(utils.FetchRoomArea(roomid))
    return roomid, area_id

class GiftConnect():
    def __init__(self, areaid=None, roomid=None):
        self.danmuji = None
        self.roomid = roomid
        self.areaid = areaid
        # self.roomid, self.areaid = get_listen_room()

    async def run(self):
        try:
            self.roomid, self.areaid = await get_listen_room()
            self.danmuji = bilibiliClient(self.roomid, self.areaid)
            while True:
                self.danmuji.roomid = self.roomid
                printer.info(['# 正在启动礼物监控弹幕姬'], True)
                time_start = int(utils.CurrentTime())
                connect_results = await self.danmuji.connectServer()
                # print(connect_results)
                if not connect_results:
                    continue
                task_main = asyncio.ensure_future(self.danmuji.ReceiveMessageLoop())
                task_heartbeat = asyncio.ensure_future(self.danmuji.HeartbeatLoop())
                task_checkarea = asyncio.ensure_future(self.danmuji.CheckArea())
                finished, pending = await asyncio.wait([task_main, task_heartbeat, task_checkarea], return_when=asyncio.FIRST_COMPLETED)
                printer.info([f'{self.areaid}号弹幕姬异常或主动断开，正在处理剩余信息'], True)
                time_end = int(utils.CurrentTime())
                if not task_heartbeat.done():
                    task_heartbeat.cancel()
                if not task_checkarea.done():
                    task_checkarea.cancel()
                task_terminate = asyncio.ensure_future(self.danmuji.close_connection())
                await asyncio.wait(pending)
                await asyncio.wait([task_terminate])
                printer.info([f'{self.areaid}号弹幕姬退出，剩余任务处理完毕'], True)
                if time_end - time_start < 10:
                    print('# 当前网络不稳定，为避免频繁不必要尝试，将自动在5秒后重试')
                    await asyncio.sleep(10)
        except:
            traceback.print_exc()




class bilibiliClient():

    __slots__ = ('ws', 'roomid', 'area_id', 'client')
    structer = struct.Struct('!I2H2I')

    def __init__(self, roomid=None, area_id=None):
        self.client = aiohttp.ClientSession()
        if roomid is None:
            self.roomid = ConfigLoader().dic_user['other_control']['default_monitor_roomid']
            self.area_id = 0
        else:
            self.roomid = roomid
            self.area_id = area_id

    # 待确认
    async def close_connection(self):
        try:
            await self.ws.close()
        except:
            print('请联系开发者', sys.exc_info()[0], sys.exc_info()[1])
        printer.info([f'{self.area_id}号弹幕收尾模块状态{self.ws.closed}'], True)

    async def CheckArea(self):
        try:
            while True:
                area_id = await asyncio.shield(utils.FetchRoomArea(self.roomid))
                if area_id != self.area_id:
                    # printer.info([f'{self.roomid}更换分区{self.area_id}为{area_id}，即将切换房间'], True)
                    return
                await asyncio.sleep(300)
        except asyncio.CancelledError:
            printer.info([f'{self.area_id}号弹幕监控分区检测模块主动取消'], True)

    async def connectServer(self):
        try:
            url = 'wss://broadcastlv.chat.bilibili.com:443/sub'

            self.ws = await asyncio.wait_for(self.client.ws_connect(url), timeout=3)
        except:
            print("# 连接无法建立，请检查本地网络状况")
            print(sys.exc_info()[0], sys.exc_info()[1])
            return False
        printer.info([f'{self.area_id}号弹幕监控已连接b站服务器'], True)
        body = f'{{"uid":0,"roomid":{self.roomid},"protover":1,"platform":"web","clientver":"1.3.3"}}'
        return (await self.SendSocketData(opt=7, body=body))

    async def HeartbeatLoop(self):
        printer.info([f'{self.area_id}号弹幕监控开始心跳（心跳间隔30s，后续不再提示）'], True)
        try:
            while True:
                if not (await self.SendSocketData(opt=2, body='')):
                    return
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            printer.info([f'{self.area_id}号弹幕监控心跳模块主动取消'], True)

    async def SendSocketData(self, opt, body, len_header=16, ver=1, seq=1):
        remain_data = body.encode('utf-8')
        len_data = len(remain_data) + len_header
        header = self.structer.pack(len_data, len_header, ver, opt, seq)
        data = header + remain_data
        try:
            await self.ws.send_bytes(data)
        except asyncio.CancelledError:
            printer.info([f'{self.area_id}号弹幕监控发送模块主动取消'], True)
            return False
        except:
            print(sys.exc_info()[0], sys.exc_info()[1])
            return False
        return True

    async def ReadSocketData(self):
        bytes_data = None
        try:
            msg = await asyncio.wait_for(self.ws.receive(), timeout=35.0)
            bytes_data = msg.data
        except asyncio.TimeoutError:
            print('# 由于心跳包30s一次，但是发现35内没有收到任何包，说明已经悄悄失联了，主动断开')
            return None
        except:
            print(sys.exc_info()[0], sys.exc_info()[1])
            print('请联系开发者')
            return None

        return bytes_data

    async def ReceiveMessageLoop(self):
            while True:
                try:
                    bytes_datas = await self.ReadSocketData()
                    if bytes_datas is None:
                        break
                    len_read = 0
                    len_bytes_datas = len(bytes_datas)
                    loop_time = 0
                    while len_read != len_bytes_datas:
                        loop_time += 1
                        if loop_time > 100:
                            print('请联系作者', bytes_datas)
                        state = None
                        split_header = self.structer.unpack(bytes_datas[len_read:16+len_read])
                        len_data, len_header, ver, opt, seq = split_header
                        remain_data = bytes_datas[len_read+16:len_read+len_data]
                        # 人气值/心跳 3s间隔
                        if opt == 3:
                            # self._UserCount, = struct.unpack('!I', remain_data)
                            printer.debug(f'弹幕心跳检测{self.area_id}')
                        # cmd
                        elif opt == 5:
                            messages = remain_data.decode('utf-8')
                            dic = json.loads(messages)
                            state = await self.handle_danmu(dic)
                        # 握手确认
                        elif opt == 8:
                            printer.info([f'{self.area_id}号弹幕监控进入房间（{self.roomid}）'], True)
                        else:
                            printer.warn(bytes_datas[len_read:len_read + len_data])

                        if state is not None and not state:
                            return
                        len_read += len_data
                except:
                    traceback.print_exc()
    async def handle_danmu(self, dic):

        try:

            await DanMuraffle(self.area_id, self.roomid, dic)

        except:
            traceback.print_exc()
