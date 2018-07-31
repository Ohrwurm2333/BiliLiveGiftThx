from bilibili import bilibili
from configloader import ConfigLoader
import random
from biliconsole import fetch_real_roomid
from statistics import Statistics
from printer import Printer
import time
import datetime
import asyncio
import printer
import login
import utils

import rafflehandler
import websockets
import struct
import json
import re
import sys
import queue


# Cen喵喵 薇尔莉特xx 小书童666
'''
{
    t: time.time()   -> int
    giftname:
    num:
    uname:

}

'''

ad = '喜欢叶叶的点个关注~有小礼物的可以喂给叶叶~嘻嘻嘻'
delay_ad = 10
last_danmu = 0
danmu_count = 0

thx_queue = queue.Queue()



async def preprocess_send_danmu_msg_web(msg, roomid):
    real_roomid = fetch_real_roomid(roomid)
    json_response = await bilibili.request_send_danmu_msg_web(msg, real_roomid)
    print(json_response)

async def get_listen_room():
    roomid = ConfigLoader().dic_user['other_control']['default_monitor_roomid']
    area_id = await asyncio.shield(utils.FetchRoomArea(roomid))
    return roomid, area_id


class GiftConnect():
    def __init__(self, areaid=0):
        self.danmuji = None
        self.roomid = None
        self.areaid = areaid

    async def run(self):
        while True:
            self.roomid, self.areaid = await get_listen_room()
            if self.roomid == 0:
                return
            print('# 正在启动礼物监控弹幕姬')
            time_start = int(utils.CurrentTime())
            self.danmuji = bilibiliClient(self.roomid, self.areaid)
            connect_results = await self.danmuji.connectServer()
            # print(connect_results)
            if not connect_results:
                continue
            task_main = asyncio.ensure_future(self.danmuji.ReceiveMessageLoop())
            task_heartbeat = asyncio.ensure_future(self.danmuji.HeartbeatLoop())
            task_checkarea = asyncio.ensure_future(self.danmuji.CheckArea())
            finished, pending = await asyncio.wait([task_main, task_heartbeat, task_checkarea], return_when=asyncio.FIRST_COMPLETED)
            # print('# 弹幕姬异常或主动断开，处理完剩余信息后重连')
            self.danmuji.connected = False
            time_end = int(utils.CurrentTime())
            if not task_heartbeat.done():
                task_heartbeat.cancel()
                await self.danmuji.close_connection()
                # print('# 弹幕主程序退出，立即取消心跳模块')
            else:
                await asyncio.wait(pending)
                # print('# 弹幕心跳模块退出，主程序剩余任务处理完毕')
            if time_end - time_start < 5:
                # print('# 当前网络不稳定，为避免频繁不必要尝试，将自动在5秒后重试')
                await asyncio.sleep(5)



async def DanMuraffle(area_id, connect_roomid, dic):
    cmd = dic['cmd']

    # if cmd == 'PREPARING':
    #     printer.info([f'{area_id}号弹幕监控房间下播({connect_roomid})'], True)
    #     return False
    if cmd == 'SYS_GIFT':
        if 'giftId' in dic:
            if str(dic['giftId']) in bilibili.get_giftids_raffle_keys():
                pass
        else:
            print(dic)
            open('sys_gift.log', 'a').write(json.dumps(dic) + '\n')
            # printer.info(['普通送礼提示', dic['msg_text']])
        return
    elif cmd == 'SEND_GIFT':
        # print(dic)
        open('send_gift.log', 'a').write(json.dumps(dic))
        num = dic.get('data').get('num')
        uname = dic.get('data').get('uname')
        giftName = dic.get('data').get('giftName')
        coin_type = dic.get('data').get('coin_type')
        add_thx(uname, num, giftName, connect_roomid, coin_type)



    elif cmd == 'SYS_MSG':
        pass


    elif cmd == 'GUARD_MSG':
        pass
        # print(dic)
        # a = re.compile(r"(?<=在主播 )\S+(?= 的直播间开通了总督)")
        # res = re.search(a, dic['msg'])
        # if res is not None:
        #     name = str(res.group())
        #     printer.info([f'{area_id}号弹幕监控检测到{name:^9}的总督'], True)
        #     rafflehandler.Rafflehandler.Put2Queue((((name,), utils.find_live_user_roomid),), rafflehandler.handle_1_room_captain)
        #     Statistics.append2pushed_raffle('总督', area_id=area_id)
    elif cmd == 'DANMU_MSG':
        await printDanMu(dic)
    elif cmd == 'GUARD_BUY':
        uname = dic['data']['username']
        item = dic['data']['gift_name']
        msg = '普天同庆! [%s]开通了[%s] 哇哇哇~' % (uname, item)
        await thx_danmu(msg, connect_roomid)
    else:
        open('other.log', 'a').write(json.dumps(dic) + '\n')



async def printDanMu(dic):
    # print(dic)

    f = 'block.json'
    pattern_black_list = [
        # {
        #     'pattern': '^\?\?\?$',
        #     'percent': 1,
        # },
        {
            'pattern': '^.*?((主播|up|你).*?真?(菜|辣鸡|垃圾)).*$',
            'percent': 0.7,
        }

    ]

    pattern_black_list = json.loads(open('block.json', 'r').read())

    global danmu_count
    global ad
    global last_danmu
    cmd = dic['cmd']
    str_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))

    if cmd == 'DANMU_MSG':
        # print(dic)
        send_time = dic['info'][0][4]
        send_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(send_time))
        author_uid = dic['info'][2][0]
        author_uname = dic['info'][2][1]
        try:
            roomid = dic['info'][3][3]  # str
        except Exception as e:
            # print(e)
            roomid = ConfigLoader().dic_user['other_control']['default_monitor_roomid']
        content = dic['info'][1]
        output = f'[{send_time_str}]{author_uname}({author_uid}):{content}'

        print(output)
        open('danmus.log', 'a').write(output + '\n')

        if '感谢[' in content or ad == content:
            return

        danmu_count += 1
        if danmu_count % 25 == 0 and time.time() - last_danmu > delay_ad:
            await send_ad(ad)
        last_danmu = time.time()
        # 黑名单检测
        # try:
        for d in pattern_black_list:
            try:
                p = ''
                _ = re.findall(d['pattern'], content)
                while(1):
                    if len(_) == 0:
                        break
                    p = _[0]
                    print(p)
                    if type(p) == type(''):
                        break
                    _ = p
                p = len(p)
                l = len(content)
                if p / l >= d['percent']:
                    block_message = f'block: {author_uname} because {content} {p/l}'
                    open('danmu.log', 'a').write(block_message + '\n')
                    print(block_message)
                    response = await bilibili.room_block_user(roomid, 1, author_uname, 720)
                    print(response)
            except IndexError:
                print(e)
            except Exception as e:
                print(e)

        return

async def send_ad(ad):
    await thx_danmu(ad)

class bilibiliClient():

    __slots__ = ('ws', 'connected', 'roomid', 'raffle_handle', 'area_id', 'structer')

    def __init__(self, roomid=None, area_id=None):
        self.ws = None
        self.connected = False
        self.structer = struct.Struct('!I2H2I')
        if roomid is None:
            self.roomid = ConfigLoader().dic_user['other_control']['default_monitor_roomid']
            self.area_id = 0
            self.raffle_handle = False
        else:
            self.roomid = roomid
            self.area_id = area_id
            self.raffle_handle = True

    # 待确认
    async def close_connection(self):
        try:
            await self.ws.close()
        except:
            print('请联系开发者', sys.exc_info()[0], sys.exc_info()[1])
        # printer.info([f'{self.area_id}号弹幕收尾模块状态{self.ws.closed}'], True)
        self.connected = False

    async def CheckArea(self):
        try:
            while self.connected:
                area_id = await asyncio.shield(utils.FetchRoomArea(self.roomid))
                if area_id != self.area_id:
                    # printer.info([f'{self.roomid}更换分区{self.area_id}为{area_id}，即将切换房间'], True)
                    return
                await asyncio.sleep(300)
        except asyncio.CancelledError:
            # printer.info([f'{self.area_id}号弹幕监控分区检测模块主动取消'], True)
            self.connected = False

    async def connectServer(self):
        try:
            self.ws = await websockets.connect('wss://broadcastlv.chat.bilibili.com/sub', timeout=3)
        except:
            # print("# 连接无法建立，请检查本地网络状况")
            print(sys.exc_info()[0], sys.exc_info()[1])
            return False
        # printer.info([f'{self.area_id}号弹幕监控已连接b站服务器'], True)
        body = f'{{"uid":0,"roomid":{self.roomid},"protover":1,"platform":"web","clientver":"1.3.3"}}'
        if (await self.SendSocketData(opt=7, body=body)):
            self.connected = True
            return True
        else:
            return False

    async def HeartbeatLoop(self):
        printer.info([f'{self.area_id}号弹幕监控开始心跳（心跳间隔30s，后续不再提示）'], True)
        try:
            while self.connected:
                if not (await self.SendSocketData(opt=2, body='')):
                    self.connected = False
                    return
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            # printer.info([f'{self.area_id}号弹幕监控心跳模块主动取消'], True)
            self.connected = False

    async def SendSocketData(self, opt, body, len_header=16, ver=1, seq=1):
        remain_data = body.encode('utf-8')
        len_data = len(remain_data) + len_header
        header = self.structer.pack(len_data, len_header, ver, opt, seq)
        data = header + remain_data
        try:
            await self.ws.send(data)
        except websockets.exceptions.ConnectionClosed:
            # print("# 主动关闭或者远端主动关闭.")
            self.connected = False
            return False
        except asyncio.CancelledError:
            # printer.info([f'{self.area_id}号弹幕监控发送模块主动取消'], True)
            self.connected = False
            return False
        except:
            print(sys.exc_info()[0], sys.exc_info()[1])
            self.connected = False
            return False
        return True

    async def ReadSocketData(self):
        bytes_data = None
        try:
            bytes_data = await asyncio.wait_for(self.ws.recv(), timeout=35.0)
        except asyncio.TimeoutError:
            # print('# 由于心跳包30s一次，但是发现35内没有收到任何包，说明已经悄悄失联了，主动断开')
            self.connected = False
            return None
        except websockets.exceptions.ConnectionClosed:
            # print("# 主动关闭或者远端主动关闭")
            self.connected = False
            return None
        except:
            # websockets.exceptions.ConnectionClosed'>
            print(sys.exc_info()[0], sys.exc_info()[1])
            # print('请联系开发者')
            self.connected = False
            return None
        # print(tmp)

        # print('测试0', bytes_data)
        return bytes_data

    async def ReceiveMessageLoop(self):
        if self.raffle_handle:
            while True:
                bytes_datas = await self.ReadSocketData()
                if bytes_datas is None:
                    break
                len_read = 0
                len_bytes_datas = len(bytes_datas)
                while len_read != len_bytes_datas:
                    state = None
                    split_header = self.structer.unpack(bytes_datas[len_read:16+len_read])
                    len_data, len_header, ver, opt, seq = split_header
                    remain_data = bytes_datas[len_read+16:len_read+len_data]
                    # 人气值/心跳 3s间隔
                    if opt == 3:
                        # self._UserCount, = struct.unpack('!I', remain_data)
                        pass
                    # cmd
                    elif opt == 5:
                        messages = remain_data.decode('utf-8')
                        dic = json.loads(messages)
                        state = await DanMuraffle(self.area_id, self.roomid, dic)
                    # 握手确认
                    elif opt == 8:
                        printer.info([f'{self.area_id}号弹幕监控进入房间（{self.roomid}）'], True)
                    else:
                        self.connected = False
                        printer.warn(bytes_datas[len_read:len_read + len_data])

                    if state is not None and not state:
                        return
                    len_read += len_data

        else:
            while True:
                bytes_datas = await self.ReadSocketData()
                if bytes_datas is None:
                    break
                len_read = 0
                len_bytes_datas = len(bytes_datas)
                while len_read != len_bytes_datas:
                    state = None
                    split_header = self.structer.unpack(bytes_datas[len_read:16+len_read])
                    len_data, len_header, ver, opt, seq = split_header
                    remain_data = bytes_datas[len_read+16:len_read+len_data]
                    # 人气值/心跳 3s间隔
                    if opt == 3:
                        # _UserCount, = struct.unpack('!I', remain_data)
                        # print('心跳信息', _UserCount)
                        pass
                    # cmd
                    elif opt == 5:
                        messages = remain_data.decode('utf-8')
                        dic = json.loads(messages)
                        state = printDanMu(dic)
                    # 握手确认
                    elif opt == 8:
                        printer.info([f'{self.area_id}号弹幕监控进入房间（{self.roomid}）'], True)
                    else:
                        self.connected = False
                        printer.warn(bytes_datas[len_read:len_read + len_data])

                    if state is not None and not state:
                        return
                    len_read += len_data



def add_thx(uname, num, giftName, roomid, coin_type):
    global thx_queue

    dic = {
        't': time.time(),
        'num': num,
        'uname': uname,
        'giftName': giftName,
        'roomid': roomid,
        'coin_type': coin_type,
    }
    thx_queue.put(dic)


async def run():
    global thx_queue
    while(True):
        length = thx_queue.qsize()
        # print('length=%d' % length)
        temp_list = []
        filter_list = []
        for i in range(length):
            temp_list.append(thx_queue.get())
        # print('---temp_list')
        # print(temp_list)
        # print('---')

        for j in temp_list:

            if len(filter_list) == 0:
                filter_list.append(j)
                continue
            added = False
            for k in range(len(filter_list)):   # 添加重复
                ans = filter_list[k]
                if j.get('uname') == ans.get('uname') and j.get('giftName') == ans.get('giftName') and j.get('roomid') == ans.get('roomid') and j.get('coin_type') == ans.get('coin_type'):
                    filter_list[k].update({
                        't': time.time(),
                        'num': ans.get('num') + j.get('num'),
                    })
                    # print(ans)
                    added = True
                # print(filter_list)
                break
            if not added:
                filter_list.append(j)


        #
        # print('filter length %d' % len(filter_list))
        # print('---filter_list')
        # print(filter_list)
        # print('---')

        for _ in range(len(filter_list)):
            thx_dic = filter_list[_]
            # print(time.time() - thx_dic['t'], thx_dic['giftName'], thx_dic['num'])
            if time.time() - thx_dic['t'] > 5:
                try:
                    if 'lc4t' in thx_dic['uname']:
                        msg = '感谢[吨吨]赠送的%d个%s mua~' % (thx_dic['num'], thx_dic['giftName'])
                    else:
                        msg = '感谢[%s]赠送的%d个%s~' % (thx_dic['uname'], thx_dic['num'], thx_dic['giftName'])
                    if thx_dic['coin_type'] == 'gold':
                        msg += ' 么么哒~'
                except Exception as e:
                    print(e)
                await thx_danmu(msg, thx_dic['roomid'])
            else:
                thx_queue.put(thx_dic)

        await asyncio.sleep(1)

async def thx_danmu(msg, roomid=253774):
    await bilibili.request_send_danmu_msg_web(msg, str(roomid))
