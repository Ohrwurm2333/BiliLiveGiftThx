from .bili_danmu import WsDanmuClient
import asyncio
import traceback
import json
import datetime
import time
import queue
from printer import info as print
from reqs.utils import UtilsReq


class DanmuGiftThx(WsDanmuClient):
    GIFT_MSG = '感谢{username}赠送的{num}个{giftname}'
    DELAY_SECOND = 3

    def set_user(self, user):
        self.user = user
        self.GIFT_QUEUE = queue.Queue()
        print(f'已关联用户{self.user.alias} -> {self._room_id}')

    async def run_sender(self):
        roomid = self._room_id
        wait_to_send_danmu = {}     # 礼物列表合并后的输出
        sem = asyncio.Semaphore(1)
        while(1):
            # 取出所有结果，添加到等待队列
            # 如果某个room-user-gift保持了5s不动，则推出
            async with sem:
                qlength = self.GIFT_QUEUE.qsize()
                cache_gift = []
                for i in range(qlength):
                    cache_gift.append(self.GIFT_QUEUE.get())
                # print(cache_gift)
                # cache_gift是所有没处理的送礼物的信息
                # 现在将他们合并为一个list
                for gift_info in cache_gift:
                    if gift_info.get('room') != roomid:
                        print('error room id')
                        exit(0)
                    username, gift_name, gift_num, t = gift_info.get('username'), gift_info.get(
                        'gift_name'), gift_info.get('gift_num'), gift_info.get('t')
                    if username not in wait_to_send_danmu:
                        wait_to_send_danmu[username] = {}    # 新建username
                    if gift_name not in wait_to_send_danmu.get(username):
                        wait_to_send_danmu[username].update(
                            {gift_name: {'gift_num': gift_num, 't': t}})   # username->gift_name
                    else:
                        # 查找已经送了的有多少
                        already_num = wait_to_send_danmu[username].get(
                            gift_name, {}).get('gift_num', 0)  # 已经送了的
                        wait_to_send_danmu[username][gift_name].update(
                            {'gift_num': gift_num + already_num, 't': t})  # 更新数量

                # print(wait_to_send_danmu)

                # 检查时间是否达到推出标准
                # 这里可以重写感谢弹幕
                for username, gifts in wait_to_send_danmu.items():
                    for gift_name, info in gifts.items():
                        gift_num = info.get('gift_num')
                        if gift_num == 0:
                            continue
                        if time.time() - info.get('t') > DanmuGiftThx.DELAY_SECOND:
                            await self.send_danmu(DanmuGiftThx.GIFT_MSG.format(username=username, num=gift_num, giftname=gift_name))
                            wait_to_send_danmu[username][gift_name].update({'gift_num': 0})
                await asyncio.sleep(1)

    async def send_danmu(self, text, default_length=30):
        msg = text[0:default_length]
        json_rsp = await self.user.req_s(UtilsReq.send_danmu, self.user, msg, self._room_id)
        raw_json = json.dumps(json_rsp, ensure_ascii=False)
        print(raw_json)
        if len(text) > default_length:
            await asyncio.sleep(1)
            await self.send_danmu(text[default_length:], default_length)

    async def handle_danmu(self, data: dict):
        cmd = data['cmd']
        try:
            if cmd == 'DANMU_MSG':
                flag = data['info'][0][9]
                if flag == 0:
                    print(
                        f"{data['info'][2][1]}({data['info'][2][0]})在{self._room_id}: {data['info'][1]}")
            elif cmd == 'SEND_GIFT':
                room_id = self._room_id
                user_id = data['data']['uid']
                username = data['data']['uname']

                gift_name = data['data']['giftName']
                gift_num = data['data']['num']
                self.GIFT_QUEUE.put({
                    'room': room_id,
                    'username': username,
                    'uid': user_id,
                    'gift_name': gift_name,
                    'gift_num': int(gift_num),
                    't': time.time(),
                })

            elif cmd == 'GUARD_BUY':
                # user_id=data['data']['uid'],
                username = data['data']['username']
                gift_name = data['data']['gift_name']
                gift_num = data['data']['num']
                await self.send_danmu(DanmuGiftThx.GIFT_MSG.format(username=username, num=gift_num, giftname=gift_name))

            elif cmd in ['WELCOME_GUARD', 'WELCOME', 'NOTICE_MSG', 'SYS_GIFT', 'ACTIVITY_BANNER_UPDATE_BLS', 'ENTRY_EFFECT', 'ROOM_RANK', 'ACTIVITY_BANNER_UPDATE_V2', 'COMBO_END', 'ROOM_REAL_TIME_MESSAGE_UPDATE', 'ROOM_BLOCK_MSG', 'WISH_BOTTLE', 'WEEK_STAR_CLOCK', 'ROOM_BOX_MASTER', 'HOUR_RANK_AWARDS', 'ROOM_SKIN_MSG', 'RAFFLE_START', 'RAFFLE_END', 'GUARD_LOTTERY_START', 'GUARD_LOTTERY_END', 'GUARD_MSG', 'USER_TOAST_MSG', 'SYS_MSG', 'COMBO_SEND', 'ROOM_BOX_USER', 'TV_START', 'TV_END', 'ANCHOR_LOT_END', 'ANCHOR_LOT_AWARD', 'ANCHOR_LOT_CHECKSTATUS', 'ANCHOR_LOT_STAR', 'ROOM_CHANGE', 'LIVE', 'new_anchor_reward', 'room_admin_entrance', 'ROOM_ADMINS', 'PREPARING']:
                pass
            else:
                print(data)
        except:
            traceback.print_exc()
            print(data)
        return True


# {"code":0,"msg":"","message":"","data":{"id":4099580,"uname":"bishi","block_end_time":"2020-01-03 17:36:18"}}
# {'code': -400, 'msg': '此用户已经被禁言了', 'message': '此用户已经被禁言了', 'data': []}
