import streamlit as st
import os
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import json
import re
from media_search import MediaSearch
import uuid
import time
from dotenv import load_dotenv
from video_generator import VideoGenerator
import glob

# 環境変数の読み込み
load_dotenv()

# NLTKのデータをダウンロード
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# アプリケーションの設定
st.set_page_config(
    page_title="TikTok動画生成ツール",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF0050;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #00F2EA;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .step-container {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #e6f7ff;
        padding: 1rem;
        border-left: 5px solid #1890ff;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #f6ffed;
        padding: 1rem;
        border-left: 5px solid #52c41a;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #fffbe6;
        padding: 1rem;
        border-left: 5px solid #faad14;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .stButton>button {
        background-color: #FF0050;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover {
        background-color: #CC0040;
    }
    .keyword-button {
        background-color: #00F2EA;
        color: black;
        border: none;
        border-radius: 20px;
        padding: 0.3rem 0.8rem;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
        display: inline-block;
    }
    .media-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 0.5rem;
        margin-bottom: 1rem;
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
        color: #888;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ディレクトリの作成
MEDIA_DIR = os.path.join(os.path.dirname(__file__), "media")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")
os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# セッション状態の初期化
if 'script' not in st.session_state:
    st.session_state.script = ""
if 'scenes' not in st.session_state:
    st.session_state.scenes = []
if 'keywords' not in st.session_state:
    st.session_state.keywords = {}
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'selected_media' not in st.session_state:
    st.session_state.selected_media = {}
if 'media_search_results' not in st.session_state:
    st.session_state.media_search_results = {}
if 'generated_video' not in st.session_state:
    st.session_state.generated_video = None
if 'video_options' not in st.session_state:
    st.session_state.video_options = {
        'duration_per_scene': 5,
        'add_title': True,
        'add_ending': True,
        'selected_bgm': None
    }

# メディア検索クライアントの初期化
media_search = MediaSearch()

# 動画生成クライアントの初期化
video_generator = VideoGenerator(output_dir=OUTPUT_DIR)

# キーワード抽出関数
def extract_keywords(text, num_keywords=5):
    # テキストをトークン化
    tokens = word_tokenize(text.lower())
    
    # ストップワードを取得（日本語と英語）
    stop_words = set(stopwords.words('english'))
    try:
        stop_words.update(stopwords.words('japanese'))
    except:
        pass  # 日本語のストップワードがない場合は無視
    
    # 記号や数字を除去
    tokens = [token for token in tokens if token.isalpha()]
    
    # ストップワードを除去
    tokens = [token for token in tokens if token not in stop_words]
    
    # 単語の頻度をカウント
    word_freq = {}
    for token in tokens:
        if token in word_freq:
            word_freq[token] += 1
        else:
            word_freq[token] = 1
    
    # 頻度順にソート
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    
    # 上位のキーワードを返す
    return [word for word, freq in sorted_words[:num_keywords]]

# シーン分割関数
def split_into_scenes(script):
    # シーンの区切りを検出（空行や特定のマーカーで区切られていると仮定）
    scenes = re.split(r'\n\s*\n', script)
    # 空のシーンを除去
    scenes = [scene.strip() for scene in scenes if scene.strip()]
    return scenes

# 台本解析関数
def analyze_script(script):
    scenes = split_into_scenes(script)
    scene_keywords = {}
    
    for i, scene in enumerate(scenes):
        keywords = extract_keywords(scene)
        scene_keywords[f"シーン{i+1}"] = {
            "text": scene,
            "keywords": keywords
        }
    
    return scenes, scene_keywords

# メディア検索関数
def search_media_for_scene(scene_id, keyword):
    # 検索結果をキャッシュするためのキー
    cache_key = f"{scene_id}_{keyword}"
    
    # キャッシュに結果があれば使用
    if cache_key in st.session_state.media_search_results:
        return st.session_state.media_search_results[cache_key]
    
    # 検索実行
    with st.spinner(f"「{keyword}」の画像を検索中..."):
        results = media_search.search_images(keyword, per_page=6)
        
    # 結果をキャッシュ
    st.session_state.media_search_results[cache_key] = results
    return results

# メディア選択関数
def select_media_for_scene(scene_id, media_item):
    if scene_id not in st.session_state.selected_media:
        st.session_state.selected_media[scene_id] = []
    
    # 既に選択されているか確認
    for item in st.session_state.selected_media[scene_id]:
        if item['id'] == media_item['id'] and item['source'] == media_item['source']:
            return  # 既に選択済み
    
    # メディアをダウンロード
    file_ext = os.path.splitext(media_item['medium_url'])[-1] or '.jpg'
    filename = f"{uuid.uuid4()}{file_ext}"
    save_path = os.path.join(MEDIA_DIR, filename)
    
    if media_search.download_media(media_item['medium_url'], save_path):
        # ダウンロードしたファイルパスを追加
        media_item['local_path'] = save_path
        st.session_state.selected_media[scene_id].append(media_item)
        return True
    return False

# 利用可能なBGMを取得
def get_available_bgm():
    bgm_files = glob.glob(os.path.join(AUDIO_DIR, "*.mp3"))
    return [os.path.basename(f) for f in bgm_files]

# 動画生成関数
def generate_video():
    try:
        with st.spinner("動画を生成中..."):
            output_filename = f"tiktok_video_{int(time.time())}.mp4"
            
            # 動画オプションを設定
            video_generator.scene_duration = st.session_state.video_options['duration_per_scene']
            video_generator.add_title = st.session_state.video_options['add_title']
            video_generator.add_ending = st.session_state.video_options['add_ending']
            
            # BGMの設定
            bgm_path = None
            if st.session_state.video_options['selected_bgm']:
                bgm_path = os.path.join(AUDIO_DIR, st.session_state.video_options['selected_bgm'])
            
            output_path = video_generator.generate_video(
                st.session_state.keywords,
                st.session_state.selected_media,
                output_filename=output_filename,
                bgm_path=bgm_path
            )
            st.session_state.generated_video = output_path
            return output_path
    except Exception as e:
        st.error(f"動画生成中にエラーが発生しました: {str(e)}")
        return None

# メインアプリケーション
def main():
    st.markdown('<h1 class="main-header">TikTok動画生成ツール</h1>', unsafe_allow_html=True)
    
    # サイドバーにステップ表示
    st.sidebar.title("進行状況")
    
    steps = ["1. 台本入力", "2. メディア選択", "3. 動画生成", "4. 出力"]
    current_step_idx = st.session_state.current_step - 1
    
    # プログレスバー
    progress_val = st.session_state.current_step / len(steps)
    st.sidebar.progress(progress_val)
    
    # ステップ表示
    for i, step in enumerate(steps):
        if i < current_step_idx:
            st.sidebar.success(step)
        elif i == current_step_idx:
            st.sidebar.info(f"➡️ {step}")
        else:
            st.sidebar.write(step)
    
    # ヘルプ情報
    with st.sidebar.expander("ヘルプ"):
        st.write("""
        ### 使い方
        1. 台本を入力し、解析ボタンをクリックします
        2. 各シーンに合った画像を検索・選択します
        3. 動画生成オプションを設定し、動画を生成します
        4. 完成した動画をダウンロードします
        
        ### ヒント
        - 各シーンは空行で区切ってください
        - キーワードをクリックすると関連画像を検索できます
        - 全てのシーンに少なくとも1つの画像を選択してください
        """)
    
    # ステップ1: 台本入力
    if st.session_state.current_step == 1:
        with st.container():
            st.markdown('<h2 class="sub-header">台本を入力</h2>', unsafe_allow_html=True)
            
            with st.expander("台本の書き方のヒント", expanded=True):
                st.markdown("""
                <div class="info-box">
                    <h4>効果的な台本の書き方</h4>
                    <ul>
                        <li>各シーンは空行で区切ってください</li>
                        <li>1シーンは約5〜10秒を目安に作成してください</li>
                        <li>全体で1分程度（6〜10シーン）が理想的です</li>
                        <li>簡潔で明確なメッセージを心がけてください</li>
                        <li>視聴者の興味を引く導入から始めましょう</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            # サンプル台本ボタン
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("料理レシピのサンプル"):
                    sample_script = """こんにちは、今日は簡単な料理レシピを紹介します。

今回作るのは、ヘルシーなアボカドトースト！

材料は、パン、アボカド、塩、こしょう、レモン汁です。

まず、アボカドを半分に切り、中身をスプーンですくい出します。

フォークでアボカドをつぶし、レモン汁、塩、こしょうを加えて混ぜます。

パンを焼いて、アボカドペーストを塗ります。

お好みでトマトや卵をトッピングしても美味しいです。

簡単で栄養満点の朝食の完成です！ぜひ試してみてください。"""
                    st.session_state.script = sample_script
            
            with col2:
                if st.button("旅行紹介のサンプル"):
                    sample_script = """京都への旅行計画を立てるなら、ぜひ参考にしてください！

まず、清水寺は外せない観光スポットです。美しい景色と歴史的建造物を楽しめます。

次に、金閣寺は金箔に覆われた美しい建物で、池の水面に映る姿も絶景です。

伏見稲荷大社の千本鳥居は、SNS映えする人気スポットになっています。

京都の食文化も魅力的で、湯葉や京懐石などの伝統料理を味わいましょう。

夜は祇園エリアで風情ある街並みを散策するのがおすすめです。

京都は四季折々の美しさがあるので、季節ごとに訪れる価値があります。

ぜひ、日本の伝統文化を体験できる京都旅行を計画してみてください！"""
                    st.session_state.script = sample_script
            
            # 台本入力エリア
            script = st.text_area("台本を入力してください", st.session_state.script, height=300)
            
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("台本を解析", use_container_width=True):
                    if not script:
                        st.error("台本を入力してください")
                    else:
                        st.session_state.script = script
                        scenes, keywords = analyze_script(script)
                        st.session_state.scenes = scenes
                        st.session_state.keywords = keywords
                        st.session_state.current_step = 2
                        st.experimental_rerun()
    
    # ステップ2: メディア選択
    elif st.session_state.current_step == 2:
        st.markdown('<h2 class="sub-header">シーンごとのキーワードとメディア選択</h2>', unsafe_allow_html=True)
        
        if not st.session_state.scenes:
            st.error("台本が解析されていません。ステップ1に戻ってください。")
            if st.button("ステップ1に戻る"):
                st.session_state.current_step = 1
                st.experimental_rerun()
        else:
            with st.expander("メディア選択のヒント", expanded=True):
                st.markdown("""
                <div class="info-box">
                    <h4>効果的な画像選択のコツ</h4>
                    <ul>
                        <li>台本の内容を視覚的に表現する画像を選びましょう</li>
                        <li>高品質で鮮明な画像を優先してください</li>
                        <li>一貫性のあるスタイルの画像を選ぶと統一感が出ます</li>
                        <li>キーワードで検索して見つからない場合は、別のキーワードを試してみましょう</li>
                        <li>各シーンに最低1枚の画像を選択する必要があります</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            st.write("台本から抽出されたシーンとキーワード:")
            
            for scene_id, scene_data in st.session_state.keywords.items():
                with st.expander(f"{scene_id}: {scene_data['text'][:50]}...", expanded=True):
                    st.write(scene_data['text'])
                    st.markdown("**抽出されたキーワード:**")
                    
                    # キーワード表示と検索ボタン
                    st.markdown('<div style="margin-bottom: 10px;">', unsafe_allow_html=True)
                    
                    # カスタムキーワード入力
                    col1, col2 = st.columns([3, 1])
                    custom_keyword = col1.text_input(f"カスタムキーワード", key=f"custom_{scene_id}")
                    search_custom = col2.button("検索", key=f"search_custom_{scene_id}")
                    
                    if search_custom:
                        if custom_keyword:
                            results = search_media_for_scene(scene_id, custom_keyword)
                            st.session_state[f"active_keyword_{scene_id}"] = custom_keyword
                    
                    # 抽出キーワードボタン
                    st.markdown('<div style="margin-top: 10px;">', unsafe_allow_html=True)
                    for i, keyword in enumerate(scene_data['keywords']):
                        if st.button(keyword, key=f"keyword_{scene_id}_{i}"):
                            results = search_media_for_scene(scene_id, keyword)
                            st.session_state[f"active_keyword_{scene_id}"] = keyword
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # アクティブなキーワードがあれば検索結果を表示
                    active_keyword = st.session_state.get(f"active_keyword_{scene_id}", None)
                    if active_keyword:
                        st.markdown(f"**「{active_keyword}」の検索結果:**")
                        results = search_media_for_scene(scene_id, active_keyword)
                        
                        if not results:
                            st.warning("検索結果がありません。別のキーワードを試してください。")
                        else:
                            # 検索結果の表示
                            cols = st.columns(3)
                            for i, item in enumerate(results):
                                col = cols[i % 3]
                                with col:
                                    st.markdown(f'<div class="media-card">', unsafe_allow_html=True)
                                    st.image(item['preview_url'], caption=f"出典: {item['source']}")
                                    if st.button("選択", key=f"select_{scene_id}_{i}"):
                                        if select_media_for_scene(scene_id, item):
                                            st.success("メディアを選択しました")
                                            time.sleep(0.5)
                                            st.experimental_rerun()
                                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # 選択済みメディアの表示
                    if scene_id in st.session_state.selected_media and st.session_state.selected_media[scene_id]:
                        st.markdown("**選択済みメディア:**")
                        selected_cols = st.columns(len(st.session_state.selected_media[scene_id]))
                        
                        for i, item in enumerate(st.session_state.selected_media[scene_id]):
                            with selected_cols[i]:
                                st.markdown(f'<div class="media-card">', unsafe_allow_html=True)
                                st.image(item['local_path'], caption=f"選択済み {i+1}")
                                if st.button("削除", key=f"remove_{scene_id}_{i}"):
                                    st.session_state.selected_media[scene_id].pop(i)
                                    st.experimental_rerun()
                                st.markdown('</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("台本入力に戻る", use_container_width=True):
                    st.session_state.current_step = 1
                    st.experimental_rerun()
            with col2:
                # 全てのシーンに少なくとも1つのメディアが選択されているか確認
                all_scenes_have_media = all(scene_id in st.session_state.selected_media and 
                                          len(st.session_state.selected_media[scene_id]) > 0 
                                          for scene_id in st.session_state.keywords)
                
                if st.button("次へ進む（動画生成）", disabled=not all_scenes_have_media, use_container_width=True):
                    st.session_state.current_step = 3
                    st.experimental_rerun()
                
                if not all_scenes_have_media:
                    st.warning("全てのシーンに少なくとも1つのメディアを選択してください")
    
    # ステップ3: 動画生成
    elif st.session_state.current_step == 3:
        st.markdown('<h2 class="sub-header">動画生成</h2>', unsafe_allow_html=True)
        
        # 選択されたシーンとメディアの概要を表示
        st.markdown("### 選択されたシーンとメディア")
        
        with st.expander("シーンとメディアの確認", expanded=True):
            for scene_id, scene_data in st.session_state.keywords.items():
                st.markdown(f"**{scene_id}**: {scene_data['text'][:100]}...")
                
                if scene_id in st.session_state.selected_media:
                    media_cols = st.columns(min(3, len(st.session_state.selected_media[scene_id])))
                    for i, item in enumerate(st.session_state.selected_media[scene_id]):
                        with media_cols[i % 3]:
                            st.image(item['local_path'], caption=f"メディア {i+1}", width=150)
                st.markdown("---")
        
        # 動画生成オプション
        st.markdown("### 動画生成オプション")
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.video_options['duration_per_scene'] = st.slider(
                "シーンあたりの秒数", 
                min_value=3, 
                max_value=10, 
                value=st.session_state.video_options['duration_per_scene'],
                step=1
            )
            
            st.session_state.video_options['add_title'] = st.checkbox(
                "タイトルスライドを追加", 
                value=st.session_state.video_options['add_title']
            )
            
            st.session_state.video_options['add_ending'] = st.checkbox(
                "エンディングスライドを追加", 
                value=st.session_state.video_options['add_ending']
            )
        
        with col2:
            # BGM選択（サンプルBGMがある場合）
            available_bgm = get_available_bgm()
            if available_bgm:
                bgm_options = ["なし"] + available_bgm
                selected_index = 0
                if st.session_state.video_options['selected_bgm'] in available_bgm:
                    selected_index = available_bgm.index(st.session_state.video_options['selected_bgm']) + 1
                
                selected_bgm = st.selectbox(
                    "BGMを選択", 
                    options=bgm_options,
                    index=selected_index
                )
                
                if selected_bgm == "なし":
                    st.session_state.video_options['selected_bgm'] = None
                else:
                    st.session_state.video_options['selected_bgm'] = selected_bgm
                    
                    # BGMプレビュー
                    if st.session_state.video_options['selected_bgm']:
                        bgm_path = os.path.join(AUDIO_DIR, st.session_state.video_options['selected_bgm'])
                        if os.path.exists(bgm_path):
                            st.audio(bgm_path)
            else:
                st.info("BGMファイルが見つかりません。audioディレクトリにMP3ファイルを追加してください。")
        
        # 動画生成ボタン
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("動画を生成", use_container_width=True):
                output_path = generate_video()
                if output_path:
                    st.success("動画の生成が完了しました！")
                    st.session_state.current_step = 4
                    st.experimental_rerun()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("メディア選択に戻る", use_container_width=True):
                st.session_state.current_step = 2
                st.experimental_rerun()
    
    # ステップ4: 出力
    elif st.session_state.current_step == 4:
        st.markdown('<h2 class="sub-header">動画出力</h2>', unsafe_allow_html=True)
        
        if st.session_state.generated_video and os.path.exists(st.session_state.generated_video):
            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            st.markdown("### 🎉 動画の生成が完了しました！")
            st.markdown("下記の動画をダウンロードして、TikTokにアップロードしてください。")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 動画ファイルの情報
            video_size = os.path.getsize(st.session_state.generated_video) / (1024 * 1024)  # MBに変換
            st.write(f"ファイル名: {os.path.basename(st.session_state.generated_video)}")
            st.write(f"ファイルサイズ: {video_size:.2f} MB")
            
            # 動画プレビュー
            st.video(st.session_state.generated_video)
            
            # ダウンロードボタン
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                with open(st.session_state.generated_video, "rb") as file:
                    st.download_button(
                        label="動画をダウンロード",
                        data=file,
                        file_name=os.path.basename(st.session_state.generated_video),
                        mime="video/mp4",
                        use_container_width=True
                    )
            
            st.markdown("""
            ### 次のステップ
            1. 動画をダウンロードしてください
            2. TikTokアプリで動画をアップロードしてください
            3. 必要に応じてTikTok内で追加編集を行ってください
            4. ハッシュタグを追加して投稿しましょう
            """)
            
            # TikTokへの投稿ヒント
            with st.expander("TikTokへの投稿ヒント", expanded=True):
                st.markdown("""
                <div class="info-box">
                    <h4>TikTokでバズるためのヒント</h4>
                    <ul>
                        <li>最適な投稿時間を選びましょう（夕方〜夜が効果的です）</li>
                        <li>トレンドのハッシュタグを活用しましょう</li>
                        <li>キャッチーなキャプションを付けましょう</li>
                        <li>コメントへの返信を積極的に行いましょう</li>
                        <li>定期的に投稿して、フォロワーを増やしましょう</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.error("動画ファイルが見つかりません。動画生成ステップに戻って再試行してください。")
            if st.button("動画生成に戻る"):
                st.session_state.current_step = 3
                st.experimental_rerun()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("動画設定を変更", use_container_width=True):
                st.session_state.current_step = 3
                st.experimental_rerun()
        with col2:
            if st.button("最初からやり直す", use_container_width=True):
                st.session_state.script = ""
                st.session_state.scenes = []
                st.session_state.keywords = {}
                st.session_state.selected_media = {}
                st.session_state.generated_video = None
                st.session_state.current_step = 1
                st.experimental_rerun()
    
    # フッター
    st.markdown('<div class="footer">TikTok動画生成ツール © 2025</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
