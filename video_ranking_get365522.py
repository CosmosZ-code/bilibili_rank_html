import requests
import json
import time
from operator import itemgetter

class BilibiliCrawler:
    def __init__(self):
        # 设置请求头，模拟浏览器访问
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com/v/popular/rank/all',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Origin': 'https://www.bilibili.com',
            'Cookie': "buvid3=2D4B09A5-0E5F-4537-9F7C-E293CE7324F7167646infoc"  # 添加一个基础的Cookie
        }
        # API接口地址
        self.video_info_api = 'https://api.bilibili.com/x/web-interface/view'  # 视频信息API
        self.online_count_api = 'https://api.bilibili.com/x/player/online/total'  # 在线人数API
        self.ranking_api = 'https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all'  # 修改为完整的排行榜API
        self.popular_api = 'https://api.bilibili.com/x/web-interface/popular'
        self.results = {}  # 存储结果

    def get_ranking_videos(self):
        """获取B站排行榜视频列表（合并官方排行榜 + 4页热门视频）"""
        try:
            # 1. 获取官方排行榜视频
            response = requests.get(self.ranking_api, headers=self.headers)
            data = response.json()
            merged_list = []
            
            if data.get('code') == 0:
                merged_list.extend(data['data']['list'])

            # 2. 分页获取热门视频（4页，每页50条）
            popular_videos = []
            for page in range(1, 5):
                params = {'pn': page, 'ps': 50}
                response_pop = requests.get(
                    self.popular_api,
                    params=params,
                    headers=self.headers,
                    timeout=10  # 增加超时限制
                )
                page_data = response_pop.json()
                
                if page_data.get('code') == 0:
                    popular_videos.extend(page_data['data']['list'])
                else:
                    print(f"热门视频第 {page} 页获取失败，code: {page_data.get('code')}")

            # 3. 合并排行榜 + 热门视频
            merged_list.extend(popular_videos)

            # 4. 去重（基于 bvid）
            unique_videos = {}
            for video in merged_list:
                bvid = video.get('bvid')
                if bvid and bvid not in unique_videos:
                    unique_videos[bvid] = video

            return list(unique_videos.values())

        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {e}")
            return []
        except Exception as e:
            print(f"处理数据失败: {e}")
            return []

    def get_online_count(self, bvid, cid):
        """获取视频实时在线观看人数
        
        Args:
            bvid: 视频的BV号
            cid: 视频的cid
        
        Returns:
            str: 格式化的在线人数，如 "1000+"、"1.2万+"
        """
        params = {
            'bvid': bvid,
            'cid': cid
        }
        try:
            response = requests.get(self.online_count_api, params=params, headers=self.headers)
            data = response.json()
            return data['data']['total'] if data['code'] == 0 else "0"
        except:
            return "0"

    def convert_count_to_number(self, count_str):
        """将格式化的人数转换为具体数字
        
        Args:
            count_str: 格式化的人数字符串，如 "1000+"、"1.2万+"
        
        Returns:
            int: 转换后的具体数字
        """
        if '万+' in count_str:
            return int(float(count_str.replace('万+', '')) * 10000)
        elif '000+' in count_str:
            return int(count_str.replace('000+', '000'))
        return int(count_str)

    def convert_number_to_count(self, num):
        """将具体数字转换为B站风格的格式化显示字符串
        
        Args:
            num (int/float): 要转换的具体数字
            
        Returns:
            str: 格式化的字符串，如 "1000+"、"1.2万+"、"1.5亿+"
        """
        if not isinstance(num, (int, float)):
            raise ValueError("输入必须是数字类型(int/float)")
        if num < 10000:
            return str(int(num))
        elif num < 100000000:  # 小于1亿
            wan = num / 10000
            if wan.is_integer():
                return f"{int(wan)}万+"
            else:
                return f"{round(wan, 1)}万+"  # 保留1位小数
        else:  # 大于等于1亿
            yi = num / 100000000
            if yi.is_integer():
                return f"{int(yi)}亿+"
            else:
                return f"{round(yi, 1)}亿+"  # 保留1位小数

    def get_video_info_play_count(self, bvid):
        """获取视频播放量 & 弹幕数
        
        Args:
            bvid: 视频的BV号
        
        Returns:
            dict: {'play_count_num':播放量数值, 'danmaku_count_num': 弹幕数值, 'play_count': 播放量, 'danmaku_count': 弹幕数}
        """
        params = {
            'bvid': bvid,
        }
        try:
            response = requests.get(self.video_info_api, params=params, headers=self.headers)
            data = response.json()
            if data['code'] == 0:
                return {
                    'play_count_num': data['data']['stat']['view'],
                    'danmaku_count_num': data['data']['stat']['danmaku'],
                    'play_count': self.convert_number_to_count(data['data']['stat']['view']),
                    'danmaku_count': self.convert_number_to_count(data['data']['stat']['danmaku'])
                }
            return {'play_count_num':0, 'danmaku_count_num':0, 'play_count': "0", 'danmaku_count': "0"}
        except:
            return {'play_count_num':0, 'danmaku_count_num':0, 'play_count': "0", 'danmaku_count': "0"}

    def display_ranking(self):
        # 按在线人数排序
        sorted_videos = sorted(self.results.items(), key=lambda x: x[1]['count_num'], reverse=True)
        
        print("\n=== B站视频实时在线人数排行榜 ===")
        print(f"更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        for i, (bvid, info) in enumerate(sorted_videos[:20], 1):  # 只显示前20个
            print(f"{i:2d}. {info['online_count']:>8} | {info['title'][:30]:30} | UP主: {info['owner']}")
        
        print("\n" + "="*50)

    def run(self):
        """主运行函数"""
        videos = self.get_ranking_videos()
        print(f"获取到 {len(videos)} 个视频")
        
        for item in videos:
            bvid = item['bvid']
            cid = item['cid']
            online_count = self.get_online_count(bvid, cid)
            count_num = self.convert_count_to_number(online_count)
            video_stats = self.get_video_info_play_count(bvid)
            
            self.results[bvid] = {
                'title': item['title'],
                'owner': item['owner']['name'],
                'mid': str(item['owner']['mid']),
                'pic': item['pic'],
                'online_count': online_count,
                'count_num': count_num,
                'play_count_num': video_stats['play_count_num'],
                'danmaku_count_num': video_stats['danmaku_count_num'],
                'play_count': video_stats['play_count'],
                'danmaku_count': video_stats['danmaku_count'],
            }
            time.sleep(1)

        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        # self.display_ranking()

if __name__ == '__main__':
    crawler = BilibiliCrawler()
    crawler.run() 