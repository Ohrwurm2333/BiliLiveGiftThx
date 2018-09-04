from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Index, DateTime
from sqlalchemy.orm import sessionmaker, relationship
from configloader import ConfigLoader


import datetime
import time
Base = declarative_base()
c = "mysql+pymysql://USERNAME:PASSWORD@IP:PORT/DB?charset=utf8"

engine = create_engine(c, max_overflow=5)



class Live(Base):
    # 表名
    __tablename__ = 'live'
    # 表字段
    id = Column(Integer, primary_key=True)  # 主键、默认自增
    roomid = Column(Integer, index=True)    # 房间ID
    cmd = Column(String(16), index=True)
    userid = Column(Integer, index=True)
    username = Column(String(32), index=True)
    giftid = Column(Integer, index=True, nullable=True)
    gift = Column(String(32), index=True, nullable=True)    # 礼物
    num = Column(String(32), index=True, nullable=True) # 礼物数量
    price = Column(Integer, index=True, nullable=True)  # 礼物价值
    coin_type = Column(String(32), index=True, nullable=True) # 礼物类型
    time = Column(DateTime, index=True, default=datetime.datetime.fromtimestamp(int(time.time())))
    content = Column(String(360), nullable=True)    # 弹幕内容




    __table_args__ = (
    UniqueConstraint('id', 'roomid', 'userid', name='uix_id_name'), # 唯一索引
    )

    # def __repr__(self):
    #     # 查是输出的内容格式，本质还是对象
    #     return "[%s]%s(%s): %s" %(self.time, self.username, self.userid, self.content, )


def init_db():
    Base.metadata.create_all(engine)


init_db()



session = sessionmaker(bind=engine) # 指定引擎
db = session()
# db.add(xx)
# db.commit()
