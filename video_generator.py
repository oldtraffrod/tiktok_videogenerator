import os
import time
from moviepy.editor import (
    TextClip, ImageClip, VideoFileClip, 
    CompositeVideoClip, concatenate_videoclips,
    ColorClip, AudioFileClip
)
from moviepy.video.fx.resize import resize
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout

class VideoGenerator:
    def __init__(self, output_dir="output"):
        """動画生成クラスの初期化"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # TikTok向けの縦型動画設定
        self.width = 1080
        self.height = 1920
        self.fps = 30
        self.font = 'Arial'
        self.font_size = 70
        
        # デフォルト設定
        self.scene_duration = 5
        self.add_title = True
        self.add_ending = True
        
    def create_text_clip(self, text, duration=3, position='center', color='white', bg_color=None):
        """テキストクリップを作成する"""
        # テキストクリップの作成
        txt_clip = TextClip(
            text, 
            fontsize=self.font_size, 
            font=self.font, 
            color=color,
            align='center',
            method='caption',
            size=(self.width - 100, None)  # 幅に余白を持たせる
        )
        
        # 背景色がある場合は背景を追加
        if bg_color:
            bg = ColorClip(
                size=(txt_clip.w + 40, txt_clip.h + 40),
                color=bg_color
            ).set_duration(duration)
            
            txt_clip = txt_clip.set_position('center')
            txt_clip = CompositeVideoClip([bg, txt_clip])
        
        # 位置設定
        if position == 'center':
            txt_clip = txt_clip.set_position(('center', 'center'))
        elif position == 'top':
            txt_clip = txt_clip.set_position(('center', 100))
        elif position == 'bottom':
            txt_clip = txt_clip.set_position(('center', self.height - txt_clip.h - 100))
        
        # 持続時間設定
        txt_clip = txt_clip.set_duration(duration)
        
        # フェードイン・アウト効果
        txt_clip = txt_clip.fx(fadein, 0.5).fx(fadeout, 0.5)
        
        return txt_clip
    
    def create_image_clip(self, image_path, duration=3, zoom=False):
        """画像クリップを作成する"""
        img_clip = ImageClip(image_path)
        
        # TikTok形式に合わせてリサイズ
        # 縦横比を維持しながら、高さまたは幅をTikTok形式に合わせる
        if img_clip.w / img_clip.h > self.width / self.height:  # 画像が横長の場合
            new_height = self.height
            new_width = int(img_clip.w * new_height / img_clip.h)
            img_clip = img_clip.resize(height=new_height)
            # 中央部分をクロップ
            x_offset = (new_width - self.width) // 2
            img_clip = img_clip.crop(x1=x_offset, y1=0, x2=x_offset + self.width, y2=self.height)
        else:  # 画像が縦長または正方形の場合
            new_width = self.width
            new_height = int(img_clip.h * new_width / img_clip.w)
            img_clip = img_clip.resize(width=new_width)
            # 中央部分をクロップ
            y_offset = (new_height - self.height) // 2 if new_height > self.height else 0
            img_clip = img_clip.crop(x1=0, y1=y_offset, x2=self.width, y2=y_offset + self.height) if new_height > self.height else img_clip
        
        # ズーム効果
        if zoom:
            zoom_factor = 1.05  # 5%ズーム
            zoomed_clip = img_clip.resize(zoom_factor)
            # 中央部分をクロップ
            x_offset = (zoomed_clip.w - img_clip.w) // 2
            y_offset = (zoomed_clip.h - img_clip.h) // 2
            zoomed_clip = zoomed_clip.crop(x1=x_offset, y1=y_offset, x2=x_offset + img_clip.w, y2=y_offset + img_clip.h)
            
            # 最初のクリップと最後のクリップを作成
            start_clip = img_clip.set_duration(duration / 2)
            end_clip = zoomed_clip.set_duration(duration / 2)
            
            # クリップを連結
            img_clip = concatenate_videoclips([start_clip, end_clip])
        
        # 持続時間設定
        img_clip = img_clip.set_duration(duration)
        
        # フェードイン・アウト効果
        img_clip = img_clip.fx(fadein, 0.5).fx(fadeout, 0.5)
        
        return img_clip
    
    def create_scene_clip(self, scene_text, media_paths, scene_duration=5):
        """シーンクリップを作成する"""
        clips = []
        
        # 各メディアの持続時間を計算
        media_duration = scene_duration / len(media_paths) if media_paths else scene_duration
        
        # メディアクリップを作成
        for i, media_path in enumerate(media_paths):
            if media_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                # 画像の場合
                clip = self.create_image_clip(
                    media_path, 
                    duration=media_duration,
                    zoom=(i % 2 == 0)  # 交互にズーム効果を適用
                )
            elif media_path.lower().endswith(('.mp4', '.mov', '.avi')):
                # 動画の場合
                video_clip = VideoFileClip(media_path)
                # 動画の長さがmedia_durationより短い場合はループ
                if video_clip.duration < media_duration:
                    n_loops = int(media_duration / video_clip.duration) + 1
                    video_clip = concatenate_videoclips([video_clip] * n_loops)
                # 指定の長さにカット
                clip = video_clip.subclip(0, media_duration)
                # TikTok形式にリサイズ
                clip = clip.resize(height=self.height)
                # 中央部分をクロップ
                x_offset = (clip.w - self.width) // 2 if clip.w > self.width else 0
                clip = clip.crop(x1=x_offset, y1=0, x2=x_offset + self.width, y2=self.height) if clip.w > self.width else clip
            else:
                # サポートされていないメディア形式
                continue
            
            clips.append(clip)
        
        # メディアがない場合は黒背景を作成
        if not clips:
            bg_clip = ColorClip(size=(self.width, self.height), color=(0, 0, 0))
            bg_clip = bg_clip.set_duration(scene_duration)
            clips.append(bg_clip)
        
        # テキストクリップを作成
        text_clip = self.create_text_clip(
            scene_text,
            duration=scene_duration,
            position='bottom',
            color='white',
            bg_color=(0, 0, 0, 128)  # 半透明の黒背景
        )
        
        # 最終的なシーンクリップを作成
        if len(clips) > 1:
            # 複数のメディアがある場合は連結
            base_clip = concatenate_videoclips(clips)
        else:
            # 1つのメディアの場合はそのまま使用
            base_clip = clips[0]
        
        # テキストをオーバーレイ
        scene_clip = CompositeVideoClip([base_clip, text_clip])
        
        return scene_clip
    
    def generate_video(self, scenes, media_dict, output_filename="tiktok_video.mp4", bgm_path=None):
        """動画を生成する"""
        scene_clips = []
        
        # タイトルクリップを作成（最初のシーンのテキストを使用）
        if self.add_title and scenes:
            first_scene_id = list(scenes.keys())[0]
            title_text = scenes[first_scene_id]['text']
            title_clip = self.create_text_clip(
                title_text,
                duration=3,
                position='center',
                color='white',
                bg_color=(0, 0, 0)
            )
            scene_clips.append(title_clip)
        
        # 各シーンのクリップを作成
        for scene_id, scene_data in scenes.items():
            scene_text = scene_data['text']
            
            # シーンに対応するメディアを取得
            media_paths = []
            if scene_id in media_dict and media_dict[scene_id]:
                media_paths = [item['local_path'] for item in media_dict[scene_id]]
            
            # シーンの長さを決定（文字数に応じて調整）
            text_length = len(scene_text)
            scene_duration = max(3, min(8, self.scene_duration))  # 最小3秒、最大8秒
            
            # シーンクリップを作成
            scene_clip = self.create_scene_clip(scene_text, media_paths, scene_duration)
            scene_clips.append(scene_clip)
        
        # エンディングクリップを作成
        if self.add_ending:
            ending_clip = self.create_text_clip(
                "ご視聴ありがとうございました！",
                duration=3,
                position='center',
                color='white',
                bg_color=(0, 0, 0)
            )
            scene_clips.append(ending_clip)
        
        # 全てのクリップを連結
        final_clip = concatenate_videoclips(scene_clips)
        
        # BGMを追加
        if bgm_path and os.path.exists(bgm_path):
            try:
                audio_clip = AudioFileClip(bgm_path)
                # 動画の長さに合わせてループまたはカット
                if audio_clip.duration < final_clip.duration:
                    n_loops = int(final_clip.duration / audio_clip.duration) + 1
                    audio_clip = concatenate_videoclips([audio_clip] * n_loops)
                audio_clip = audio_clip.subclip(0, final_clip.duration)
                # 音量を調整
                audio_clip = audio_clip.volumex(0.5)
                # 音声を設定
                final_clip = final_clip.set_audio(audio_clip)
            except Exception as e:
                print(f"BGM追加エラー: {e}")
        
        # 出力ファイルパスを設定
        output_path = os.path.join(self.output_dir, output_filename)
        
        # 動画を書き出し
        final_clip.write_videofile(
            output_path,
            fps=self.fps,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            threads=4
        )
        
        return output_path
