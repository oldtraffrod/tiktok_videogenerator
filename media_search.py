import os
from dotenv import load_dotenv
import requests
from pixabay import Image as PixabayImage
from pexels_api import API as PexelsAPI
from python_unsplash import Unsplash

# 環境変数の読み込み
load_dotenv()

class MediaSearch:
    def __init__(self):
        # APIキーの取得（実際の使用時は.envファイルから読み込む）
        self.pixabay_api_key = os.getenv('PIXABAY_API_KEY', '')
        self.pexels_api_key = os.getenv('PEXELS_API_KEY', '')
        self.unsplash_access_key = os.getenv('UNSPLASH_ACCESS_KEY', '')
        self.unsplash_secret_key = os.getenv('UNSPLASH_SECRET_KEY', '')
        
        # APIクライアントの初期化
        self.init_api_clients()
    
    def init_api_clients(self):
        """APIクライアントを初期化する"""
        # Pixabay
        if self.pixabay_api_key:
            self.pixabay_client = PixabayImage(self.pixabay_api_key)
        else:
            self.pixabay_client = None
            
        # Pexels
        if self.pexels_api_key:
            self.pexels_client = PexelsAPI(self.pexels_api_key)
        else:
            self.pexels_client = None
            
        # Unsplash
        if self.unsplash_access_key and self.unsplash_secret_key:
            self.unsplash_client = Unsplash(
                self.unsplash_access_key,
                self.unsplash_secret_key
            )
        else:
            self.unsplash_client = None
    
    def search_pixabay_images(self, keyword, per_page=5):
        """Pixabayから画像を検索する"""
        if not self.pixabay_client:
            return []
        
        try:
            # 日本語キーワードの場合はエンコードする
            encoded_keyword = requests.utils.quote(keyword)
            response = self.pixabay_client.search(
                q=encoded_keyword,
                lang='ja',
                image_type='photo',
                orientation='vertical',  # TikTok向けに縦長画像
                per_page=per_page
            )
            
            results = []
            if 'hits' in response:
                for hit in response['hits']:
                    results.append({
                        'id': hit['id'],
                        'preview_url': hit['previewURL'],
                        'medium_url': hit['webformatURL'],
                        'large_url': hit['largeImageURL'],
                        'source': 'Pixabay',
                        'source_url': hit['pageURL'],
                        'width': hit['webformatWidth'],
                        'height': hit['webformatHeight'],
                        'tags': hit['tags']
                    })
            return results
        except Exception as e:
            print(f"Pixabay検索エラー: {e}")
            return []
    
    def search_pexels_images(self, keyword, per_page=5):
        """Pexelsから画像を検索する"""
        if not self.pexels_client:
            return []
        
        try:
            self.pexels_client.search(keyword, page=1, results_per_page=per_page)
            photos = self.pexels_client.get_entries()
            
            results = []
            for photo in photos:
                results.append({
                    'id': photo.id,
                    'preview_url': photo.src['tiny'],
                    'medium_url': photo.src['medium'],
                    'large_url': photo.src['large'],
                    'source': 'Pexels',
                    'source_url': photo.url,
                    'width': photo.width,
                    'height': photo.height,
                    'photographer': photo.photographer
                })
            return results
        except Exception as e:
            print(f"Pexels検索エラー: {e}")
            return []
    
    def search_unsplash_images(self, keyword, per_page=5):
        """Unsplashから画像を検索する"""
        if not self.unsplash_client:
            return []
        
        try:
            response = self.unsplash_client.search_photos(keyword, per_page=per_page, orientation='portrait')
            
            results = []
            if hasattr(response, 'results'):
                for photo in response.results:
                    results.append({
                        'id': photo.id,
                        'preview_url': photo.urls.thumb,
                        'medium_url': photo.urls.small,
                        'large_url': photo.urls.regular,
                        'source': 'Unsplash',
                        'source_url': photo.links.html,
                        'width': photo.width,
                        'height': photo.height,
                        'photographer': photo.user.name
                    })
            return results
        except Exception as e:
            print(f"Unsplash検索エラー: {e}")
            return []
    
    def search_images(self, keyword, per_page=5):
        """すべてのAPIから画像を検索する"""
        results = []
        
        # Pixabayから検索
        pixabay_results = self.search_pixabay_images(keyword, per_page)
        results.extend(pixabay_results)
        
        # Pexelsから検索
        pexels_results = self.search_pexels_images(keyword, per_page)
        results.extend(pexels_results)
        
        # Unsplashから検索
        unsplash_results = self.search_unsplash_images(keyword, per_page)
        results.extend(unsplash_results)
        
        return results
    
    def search_videos(self, keyword, per_page=3):
        """動画を検索する（現在はPixabayのみ）"""
        # 実装予定
        return []
    
    def download_media(self, url, save_path):
        """メディアをダウンロードする"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            
            return True
        except Exception as e:
            print(f"ダウンロードエラー: {e}")
            return False
