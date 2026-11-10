"""
こうかとん最終決戦（仮）

第4回「真・こうかとん無双」から追加機能を外し，チーム共通の部分を足したベース

【担当の印】自分の担当の印をCtrl+Fで検索すると，書く場所が見つかる
    【中川】ボス戦（ボス・ボスの弾・HPバー）
    【A】アイテムドロップ
    【B】自機強化（段階強化ショット・必殺技）
    【C】雑魚敵バリエーション・難易度上昇
    【D】画面遷移（タイトル・結果画面・リトライ）・BGM・効果音
"""
import math
import os
import random
import sys
import time

import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
BOSS_SCORE = 500  # ボス戦に切り替わるスコア
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ===== 【中川】ボス戦の定数はここに書く =====

# ===== 【A】アイテムドロップの定数はここに書く =====

# ===== 【B】自機強化の定数はここに書く =====

# ===== 【C】雑魚敵・難易度の定数はここに書く =====

# ===== 【D】画面遷移・サウンドの定数はここに書く =====


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトル（長さ1）を表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    if norm == 0:  # 同じ位置にいるときは0で割らないように下向きを返す
        return 0.0, 1.0
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]) -> None:
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.life = 3  # 残機（0になったらゲームオーバー）

    def change_img(self, num: int, screen: pg.Surface) -> None:
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface) -> None:
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス（ボスの弾もbombsグループに入れる約束）
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird) -> None:
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機（rectを持っていればボスでもよい）
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6

    def update(self) -> None:
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird) -> None:
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        # 【B】角度の引数 angle0: float = 0 はここに足す
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10
        self.power = 1  # 威力（敵やボスに与えるダメージ）

    def update(self) -> None:
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int) -> None:
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス（rectを持っていれば何でもよい）
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self) -> None:
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10 % 2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    【C】ジグザグ・追いかけ・硬い敵は，このクラスを継承して作る
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]

    def __init__(self) -> None:
        """
        敵機の画像，出現位置，停止位置，爆弾投下インターバルを設定する
        """
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル
        self.hp = 1  # 体力（0以下になったら倒れる）

    def take_damage(self, amount: int) -> None:
        """
        敵機にダメージを与え，体力を減らす
        引数 amount：与えるダメージ量（ビームのpowerなど）
        """
        self.hp -= amount

    def update(self) -> None:
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self) -> None:
        """
        スコアの文字Surfaceを画面左下に用意する
        """
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface) -> None:
        """
        現在のスコアを表示する
        引数 screen：画面Surface
        """
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class LifeDisplay:
    """
    こうかとんの残機を画面右下に文字で表示するクラス
    """
    def __init__(self) -> None:
        """
        残機表示用のフォントを用意する
        """
        self.font = pg.font.Font(None, 50)
        self.color = (255, 0, 0)

    def update(self, screen: pg.Surface, life: int) -> None:
        """
        現在の残機を表示する
        引数1 screen：画面Surface
        引数2 life：こうかとんの残機
        """
        image = self.font.render(f"LIFE: {life}", 0, self.color)
        rect = image.get_rect()
        rect.center = WIDTH-100, HEIGHT-50
        screen.blit(image, rect)


# ===== 【中川】ボス戦のクラス（Boss，BossBullet，BossHPBar）はここに書く =====


# ===== 【A】アイテムのクラス（Item）はここに書く =====


# ===== 【B】自機強化のクラス（PowerUp，SpecialGauge，Special）はここに書く =====


# ===== 【C】雑魚敵のサブクラス（ZigzagEnemy，ChaseEnemy，TankEnemy）と出現用の関数はここに書く =====


# ===== 【D】画面遷移・サウンドのクラス（TitleScreen，ResultScreen，SoundManager）はここに書く =====
class TitleScreen:
    """
    タイトルの文字を表示するクラス
    """
    def __init__(self):
        """
        タイトル画面用のフォントを用意する
        """
        self.title_font = pg.font.SysFont("hg明朝b", 100) #タイトルのフォント
        self.small_font = pg.font.Font(None, 50) #案内のフォント
        self.title_surface = self.title_font.render("こうかとん最終決戦", True, (0, 0, 0)) #タイトルのSurface作成
        self.small_surface = self.small_font.render("Press Enter", True, (0, 0, 0)) #案内のSurface作成

    def draw(self, screen: pg.Surface, tmr: int) -> None:
        """
        タイトル文字を表示する
        引数1 screen：画面Surface
        引数2 tmr：ゲーム開始からのフレーム数
        """
        screen.blit(self.title_surface, [100, 200]) #タイトルのblit
        if (tmr//25)%2 == 0:
            screen.blit(self.small_surface, [500, 350]) #案内のblit


class ResultScreen:
    """
    リザルト画面を表示するクラス
    """
    def __init__(self, kind: str):
        """
        表示するフォント、文字、画像を用意する
        """
        self.black_img = pg.Surface((WIDTH, HEIGHT))  # Surfaceの生成
        pg.draw.rect(self.black_img, (0, 0, 0), (0, 0, WIDTH, HEIGHT), width=0)  # 黒画像の描画
        self.black_img.set_alpha(200)  # 透明度の調整
        self.font = pg.font.Font(None, 80)  # フォントの設定
        self.value = 0
        self.retry = self.font.render("Press Enter to retry", True, (255, 255, 255)) #Retry文のSurface作成
        if kind == "gameover":
            self.txt = self.font.render("Game Over", True, (255, 255, 255))  # 文字の決定
            self.koukaton_img = pg.image.load("fig/8.png")  # 画像の読み込み
        elif kind == "clear":
            self.txt = self.font.render("Clear!", True, (255, 255, 255))  # 文字の決定
            self.koukaton_img = pg.image.load("fig/6.png") #画像の読み込み
        

    def draw(self, screen: pg.Surface, score_value: int) -> None:
        """
        ゲームオーバー、クリア画面、リザルトを表示する
        引数1 screen：画面Surface
        引数2 score_value：スコアの値
        """
        score_surface = self.font.render(f"Score : {score_value}", True, (255, 255, 255)) #スコアSurface作成
        screen.blit(self.black_img, [0, 0]) #透明な黒のblit
        screen.blit(self.txt, [400, 300]) #"Game Over" or "Clera"のblit
        screen.blit(self.koukaton_img, [300, 300]) #こうかとん1枚目のblit
        screen.blit(self.koukaton_img, [800, 300]) #こうかとん2枚目のblit
        screen.blit(score_surface, [500, 400]) #Scoreのblit
        screen.blit(self.retry, [500, 470]) #"Press Enter to Retry"のblit


class SoundManager:
    """
    音を管理するクラス
    """
    def __init__(self):
        """
        音源の読み込み
        """
        self.title_bgm = pg.mixer.Sound("sound/picopicodisco.mp3") #タイトルBGM
        self.normal_bgm = pg.mixer.Sound("sound/house_lo.wav") #通常時BGM
        self.boss_bgm = pg.mixer.Sound("sound/icarusnotsuiraku.mp3") #ボス戦BGM
        self.boom = pg.mixer.Sound("sound/boom.wav") #爆発音
        self.beem = pg.mixer.Sound("sound/beem.mp3") #ビーム発射音
        self.damage = pg.mixer.Sound("sound/damage.mp3") #被弾音
        self.sound_dic = {"boom":self.boom, "normal_bgm":self.normal_bgm, "beem":self.beem, "damage":self.damage}
        self.current_bgm = ""

    def play_bgm(self, name: str) -> None:
        """
        BGMの管理をする
        引数1 name：BGMの名前の文字列
        """
        if name != self.current_bgm: #current_bgmとnameの値が異なるなら
            if name == "":
                pg.mixer.music.stop() #空文字が渡されたらBGM停止
            else:
                pg.mixer.music.load(name) #nameのBGMをロード
                pg.mixer.music.play(loops = -1) #ロードしたBGMをループ再生
            self.current_bgm = name #current_bgmの値をnameにする

    def play_se(self, name: str) -> None:
        """
        効果音の管理をする
        引数1 name：効果音の名前の文字列
        """
        se = self.sound_dic[name]
        se.play()


def main() -> None:
    """
    ゲームの初期化とメインループ
    """
    pg.display.set_caption("こうかとん最終決戦（仮）")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()
    life_display = LifeDisplay()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()  # 敵の弾（ボスの弾も入れる）
    beams = pg.sprite.Group()  # こうかとんのビーム
    exps = pg.sprite.Group()  # 爆発エフェクト
    emys = pg.sprite.Group()  # 雑魚敵（Enemyのサブクラスも入れる）

    # ゲームの状態："play"（通常）／"boss"（ボス戦）
    # 【D】"title"，"gameover"，"clear"を追加する
    state = "title" #ゲームの状態を管理

    # ===== 【中川】ボス用のGroup（bosses）と変数はここで作る =====

    # ===== 【A】アイテム用のGroup（items）と威力アップの残り時間はここで作る =====

    # ===== 【B】PowerUp，SpecialGauge，Special用のGroupはここで作る =====

    # ===== 【D】TitleScreen，ResultScreen，SoundManagerはここで作る =====
    title = TitleScreen()
    gameover_result = ResultScreen("gameover")
    clear_result = ResultScreen("clear")
    sound = SoundManager()

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                # 【A】威力アップ中は作ったビームのpowerを+1する
                # 【B】強化段階の角度ごとにビームを作る形に変える
                # 【D】ビームの効果音を鳴らす
                beams.add(Beam(bird))
                sound.play_se("beem")

            # ===== 【B】Xキーで必殺技を発動する処理はここに書く =====

            # ===== 【D】Enterキーでスタート・リトライする処理はここに書く =====
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                if state == "title":
                    state = "play" #titleからplayに移行
                elif state == "play":
                    pass
                else:
                    beams.empty() #beamsを空に
                    bombs.empty() #bombsを空に
                    emys.empty() #emysを空に
                    exps.empty() #expsを空に
                    score = Score() #スコアを初期値にリセット\
                    life_display = LifeDisplay() #体力の表示をリセット
                    bird = Bird(3, (900, 400)) #こうかとんの位置をリセット
                    state = "play" #gameover or clearからplayに移行

        # ===== 【D】stateに合わせてBGMを切り替える処理の位置を変更しました ===== 
        if state == "play":
            sound.play_bgm("sound/house_lo.wav")
        elif state == "title":
            sound.play_bgm("sound/picopicodisco.mp3")
        elif state == "boss":
            sound.play_bgm("sound/icarusnotsuiraku.mp3")
        else:
            sound.play_bgm("")

        # ===== 【D】タイトル画面・結果画面を描いてcontinueする処理はここに書く =====
        if state == "title": 
            screen.blit(bg_img, (0, 0)) #背景の表示
            title.draw(screen, tmr) #タイトルを表示
            pg.display.update() #画面の更新
            clock.tick(50)
            continue
        elif state == "gameover":
            screen.blit(bg_img, (0, 0)) #背景の表示
            gameover_result.draw(screen, score.value) #ゲームオーバーを表示
            pg.display.update() #画面の更新
            clock.tick(50)
            continue
        elif state == "clear":
            screen.blit(bg_img, (0, 0)) #背景の表示
            clear_result.draw(screen, score.value) #クリア画面を表示
            pg.display.update() #画面の更新
            clock.tick(50)
            continue
        screen.blit(bg_img, (0, 0))

        # ===== 【D】stateに合わせてBGMを切り替える処理はここに書く =====
        # if state == "play":
        #     sound.play_bgm("sound/house_lo.wav")
        # else:
        #     sound.play_bgm("")

        # 雑魚敵の出現（通常プレイ中だけ）
        if state == "play":
            # 【C】スコアに応じて出現間隔と種類を変える
            if tmr % 200 == 0:  # 200フレームに1回，敵機を出現させる
                emys.add(Enemy())

        # スコアがBOSS_SCOREを超えたらボス戦へ
        if state == "play" and score.value >= BOSS_SCORE:
            state = "boss"

        # ===== 【中川】ボスを登場させる処理・ボスの攻撃はここに書く =====

        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        # ビームと雑魚敵の当たり判定（敵は消さずにダメージを与える）
        for emy, hit_beams in pg.sprite.groupcollide(emys, beams, False, True).items():
            for beam in hit_beams:
                emy.take_damage(beam.power)
            if emy.hp <= 0:
                # ===== ここが「敵が倒れた瞬間」 =====
                exps.add(Explosion(emy, 100))  # 爆発エフェクト
                score.value += 10  # 10点アップ
                bird.change_img(6, screen)  # こうかとん喜びエフェクト
                # 【A】確率でアイテムを出す
                # 【B】必殺技のゲージを溜める
                # 【D】爆発の効果音を鳴らす
                emy.kill()

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        # ===== 【中川】ビームとボスの当たり判定はここに書く =====

        # ===== 【A】こうかとんがアイテムを取ったときの処理はここに書く =====

        # ===== 【C】追いかけ敵の体当たり（こうかとんと雑魚敵の当たり判定）はここに書く =====

        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))
            bird.change_img(8, screen)  # こうかとん悲しみエフェクト
            bird.life -= 1
            # 【D】被弾の効果音を鳴らす
            sound.play_se("damage")
        if bird.life <= 0:
            # 【D】ここをstate = "gameover"にする（今はゲームを終了する）
            state = "gameover" #こうかとんの体力が0ならgameover

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)

        # ===== 【中川】ボスとHPバーの描画はここに書く =====

        # ===== 【A】アイテムの描画（items.update，items.draw）はここに書く =====

        # ===== 【B】強化段階・ゲージ・必殺技の描画はここに書く =====

        score.update(screen)
        life_display.update(screen, bird.life)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
