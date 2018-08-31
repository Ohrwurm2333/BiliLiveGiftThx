from bilibili import bilibili
from configloader import ConfigLoader
import random
from utils import check_room
from statistics import Statistics
from printer import Printer
import time
import datetime
import asyncio
import printer
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


ad = '喜欢叶叶的点个关注~有小礼物的可以喂给叶叶~嘻嘻嘻'
delay_ad = 10
last_danmu = 0
danmu_count = 0

thx_queue = queue.Queue()





async def DanMuraffle(area_id, connect_roomid, dic):
    cmd = dic['cmd']
    if cmd == 'SEND_GIFT':
        num = dic.get('data').get('num')
        uname = dic.get('data').get('uname')
        uid = dic.get('data').get('uid')
        giftName = dic.get('data').get('giftName')
        coin_type = dic.get('data').get('coin_type')
        gift_id = dic['data']['giftId']
        price = dic.get('data').get('total_coin')
        db.add(Live(
            roomid=int(connect_roomid),
            cmd=cmd,
            userid=int(uid),
            num=num,
            username=uname,
            giftid=int(gift_id),
            gift=giftName,
            coin_type=coin_type,
            price=price,

        ))
        db.commit()
        add_thx(uname, num, giftName, connect_roomid, coin_type)

    elif cmd == 'DANMU_MSG':
        send_time = dic['info'][0][4]
        author_uid = dic['info'][2][0]
        author_uname = dic['info'][2][1]
        content = dic['info'][1]

        try:
            db.add(Live(
                roomid=int(connect_roomid),
                cmd=cmd,
                time=datetime.datetime.fromtimestamp(int(send_time)),
                userid=author_uid,
                username=author_uname,
                content=content
            ))
            db.commit()
        except:
            traceback.print_exc()
        try:
            await DanMuMsgHandle(dic)
        except:
            traceback.print_exc()
    elif cmd == 'GUARD_BUY':
        uname = dic['data']['username']
        uid = dic['data']['uid']
        item = dic['data']['gift_name']
        gift_id = dic['data']['giftId']
        price = dic['data']['price']
        num = dic['data']['num']
        msg = '普天同庆! [%s]开通了[%s] 哇哇哇~' % (uname, item)
        db.add(Live(
            roomid=int(connect_roomid),
            cmd=cmd,
            userid=int(uid),
            username=uname,
            giftid=int(gift_id),
            gift=item,
            num=num,
            coin_type='gold',
            price=price
        ))
        db.commit()
        await thx_danmu(msg, connect_roomid)
    elif cmd in ['SYS_GIFT', 'SPECIAL_GIFT', 'ENTRY_EFFECT', 'SYS_MSG', 'GUARD_MSG', 'ENTRY_EFFECT', 'COMBO_SEND', 'COMBO_END', 'ROOM_RANK']:
        return
    elif cmd in ['WELCOME_GUARD', 'WELCOME']:
        try:
            username = dic['data']['uname'] if cmd =='WELCOME' else dic['data']['username']
            db.add(Live(
                roomid=int(connect_roomid),
                cmd=cmd,
                userid=dic['data']['uid'],
                username=username,
            ))
            db.commit()
        except:
            traceback.print_exc()
            print(dic)

    elif cmd in ['WISH_BOTTLE']:
        db.add(Live(
            roomid=int(connect_roomid),
            cmd=cmd,
            userid=0,
            username=cmd,
            content=json.dumps(dic['data'],ensure_ascii=False)
        ))
        db.commit()
    else:
        open('other.log', 'a').write(json.dumps(dic) + '\n')



async def DanMuMsgHandle(dic):
    # print(dic)

    data_list = json.loads(open('data.json', 'r').read())
    pattern_black_list = data_list.get('block')


    global danmu_count
    global ad
    global last_danmu
    cmd = dic['cmd']
    str_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))

    if cmd == 'DANMU_MSG':
        send_time = dic['info'][0][4]
        send_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(send_time))
        author_uid = dic['info'][2][0]
        author_uname = dic['info'][2][1]
        try:
            roomid = dic['info'][3][3]  # str
        except Exception as e:
            roomid = ConfigLoader().dic_user['other_control']['default_monitor_roomid']
        content = dic['info'][1]
        output = f'[{send_time_str}]{author_uname}({author_uid}):{content}'

        print(output)

        if '感谢[' in content or ad == content:
            return

        danmu_count += 1
        if danmu_count > 25 and time.time() - last_danmu > delay_ad:
            danmu_count = 0
            await send_ad(ad)
        last_danmu = time.time()

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
                    print(p/l)
                    block_message = f'block: {author_uname} because {content} {p/l}'
                    response = await bilibili.room_block_user(roomid, 1, author_uname, 720)
                    await thx_danmu('auto block user[%s]' % author_uname)
                    print(response)
                    return
            except IndexError:
                print(e)
            except Exception as e:
                print(e)

        for key, value in data_list.get('data').items():
            # car : '上车'

            check = data_list.get(key)  # 匹配序列
            for d in check:
                # try:
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
                    print(p/l)
                    response = await thx_danmu(value)
                    # print(response)
                    return
        return

async def send_ad(ad):
    await asyncio.sleep(5)
    await thx_danmu(ad)



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
        temp_list = []
        filter_list = []
        for i in range(length):
            temp_list.append(thx_queue.get())


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
                    added = True
                break
            if not added:
                filter_list.append(j)


        for _ in range(len(filter_list)):
            thx_dic = filter_list[_]
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


async def thx_danmu(msg, roomid=None):
    if roomid is None:
        roomid = ConfigLoader().dic_user['other_control']['default_monitor_roomid']
    if len(str(roomid)) < 6:
        real_roomid = await check_room(roomid)
    else:
        real_roomid = roomid
    json_response = await bilibili.request_send_danmu_msg_web(msg, real_roomid)
