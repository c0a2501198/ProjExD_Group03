"""
こうかとん最終決戦（仮）

第4回「真・こうかとん無双」から追加機能を外し，チーム共通の部分を足したベース

【担当の印】自分の担当の印をCtrl+Fで検索すると，書く場所が見つかる
    【中川】ボス戦（ボス・ボスの弾・HPバー）
    【A】アイテムドロップ
    【仙田】自機強化（段階強化ショット・必殺技）
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
BOSS_SCORE = 700  # ボス戦に切り替わるスコア
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ===== 【中川】ボス戦の定数はここに書く =====
BOSS_HP=100
BOSS_STOP_Y=150
BOSS_SWING_WIDTH=300
BOSS_SWING_SPEED=0.02
BOSS_INTERVALS=[60,80,30]
BOSS_BONUS=500
BOSS_BAR_WIDTH=600
BOSS_BAR_HEIGHT=20
BOSS_BAR_Y=30
BOSS_BAR_COLORS: list[tuple[int, int, int]] = [(0, 200, 0), (230, 200, 0), (220, 0, 0)]

# ===== 【A】アイテムドロップの定数はここに書く =====
ITEM_DROP_RATE = 0.2  # アイテムが出る確率（20%）
ITEM_SPEED = 3        # アイテムが落ちる速さ
LIFE_MAX = 5          # 回復したときの残機の上限
POWER_TIME = 500      # 威力アップが続くフレーム数（約10秒）
BONUS_SCORE = 30      # スコアアイテムで増える点数

# ===== 【仙田】自機強化の定数はここに書く =====
LEVEL_SCORES = [0, 100, 300]  # Lv1, Lv2, Lv3 になるスコア
GAUGE_MAX = 100  # ゲージの最大値
GAUGE_PER_ENEMY = 10  # 雑魚敵1体を倒したときに溜まるゲージ量
SPECIAL_MAX_USE = 3  # 必殺技を使える最大回数
SPECIAL_TIME = 30  # 必殺技の白い画面エフェクトを表示するフレーム数
SPECIAL_DAMAGE = 10  #ボス戦で必殺技使用時に使われる

# ===== 【C】雑魚敵・難易度の定数はここに書く =====

ZIGZAG_WIDTH = 100
ZIGZAG_SPEED = 0.05
CHASE_SPEED = 5
TANK_HP = 3
SPAWN_INTERVALS = [200, 150, 100]
SPAWN_SCORES = [0, 100, 300]
FIRE_INTERVALS = [200, 150, 100]  
BOMB_SPEEDS = [6, 8, 10]  

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

    def __init__(self, emy: "Enemy", bird: Bird, speed: int = 6) -> None:
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機（rectを持っていればボスでもよい）
        引数2 bird：攻撃対象のこうかとん
        引数3 speed：爆弾の移動速度
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
        self.speed = speed # スコアに応じて爆弾の速度を設定する

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
    def __init__(self, bird: Bird, angle0: float = 0) -> None:
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        # 【仙田】角度の引数 angle0: float = 0 はここに足す
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle + angle0, 1.0)  # angle0 だけ角度をずらす
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.radian = math.radians(angle + angle0)  # ずらした角度をラジアンに変換
        self.x = math.cos(self.radian)  # 進行方向のx成分
        self.y = -math.sin(self.radian)  # 進行方向のy成分（画面は下が+なので符号を反転）
        self.speed = 10
        self.power = 1  # 威力（敵やボスに与えるダメージ）

    def update(self) -> None:
        """
        ビームを速度ベクトルself.x, self.yに基づき移動させる
        """
        self.rect.move_ip(self.speed*self.x, self.speed*self.y)
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
        self.timer = 0
        self.hp = 2  # 体力（0以下になったら倒れる）

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
class Boss(pg.sprite.Sprite):
    """
    ボスに関するクラス
    スコアが一定に達すると登場して画面上部まで降りてきて，左右に揺れながら攻撃する
    HPの残りに応じて攻撃パターンが変わる
    """
    def __init__(self,bird: Bird) -> None:
        """
        ボスの画像・位置・HP・状態を設定する
        引数 bird：狙うこうかとん
        """
        super().__init__()
        self.bird=bird
        Boss_image=pg.image.load("fig/alien1.png")
        self.image=pg.transform.rotozoom(Boss_image,0,2.5)
        self.rect=self.image.get_rect()
        self.rect.center=(WIDTH//2),(-100)
        self.hp=BOSS_HP
        self.max_hp=BOSS_HP
        self.mode="enter"  # "enter"（登場中）／"fight"（戦闘中）／"dying"（撃破）
        self.count=0
        self.blink=0

    def update(self) -> None:
        """
        modeに合わせてボスを動かす
        "enter"は降下，"fight"は左右に揺れる，フェーズ2は揺れが速くなる
        """
        if self.mode=="enter":
            self.rect.move_ip(0,10)
            if self.rect.centery>=BOSS_STOP_Y:
                self.mode="fight"
        elif self.mode=="fight":
            if self.get_phase()==2:
                self.count+=2
            else:
                self.count+=1
            self.rect.centerx=WIDTH // 2 + BOSS_SWING_WIDTH * math.sin(self.count * BOSS_SWING_SPEED)

    def take_damage(self,amount:int) -> None:
        """
        HPを減らす．"fight"のときだけ減り，0になったら"dying"にする
        引数 amount：ダメージ量
        """
        if self.mode=="fight":
            self.hp=max(self.hp-amount,0)
            if self.hp==0:
                self.mode="dying"

    def get_phase(self) ->int:
        """
        HPの割合から現在のフェーズを求める
        戻り値：0（HP50%より多い），1（20%より多い），2（20%以下）
        """
        hp_ratio=self.hp/self.max_hp
        if hp_ratio>0.5:
            ans=0
        elif hp_ratio>0.2:
            ans=1
        else:
            ans=2
        return ans 

    def attack(self,tmr: int) -> list[pg.sprite.Sprite]:
        """
        攻撃するタイミングなら弾を作って返す
        フェーズ0は狙い撃ち，1と2は扇状の5発
        引数 tmr：経過フレーム
        戻り値：弾のリスト（攻撃しないときは空のリスト）
        """
        phase=self.get_phase()
        if self.mode!="fight" or tmr%BOSS_INTERVALS[phase]!=0:
            return []
        if phase==0:
            return [Bomb(self,self.bird)]
        elif phase==1 or phase==2:
            return [BossBullet(self, angle) for angle in range(60, 121, 15)]

        
class BossBullet(pg.sprite.Sprite):
    """
    ボスが扇状に撃つ弾に関するクラス
    指定した角度へまっすぐ飛ぶ
    """
    def __init__(self,boss:Boss,angle:float) -> None:
        """
        弾の見た目・位置・速度を設定する
        引数1 boss：弾を撃つボス
        引数2 angle：飛ぶ角度（度，90が真下）
        """
        super().__init__()
        rad=8
        self.boss=boss
        self.angle=angle
        self.image = pg.Surface((2*rad, 2*rad))
        pg.draw.circle(self.image, (255, 0, 255), (rad, rad), rad)  # 例: 紫
        self.image.set_colorkey((0, 0, 0))
        self.rect=self.image.get_rect()
        self.rect.centerx=self.boss.rect.centerx
        self.x = self.rect.centerx
        self.rect.centery=self.boss.rect.centery +10
        self.y = self.rect.centery
        self.theta=math.radians(angle)
        self.vx=math.cos(self.theta)*5
        self.vy=math.sin(self.theta)*5

    def update(self) -> None:
        """
        小数の位置x・yに速度を足して弾を動かし，画面外に出たら消す
        """
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (self.x, self.y)
        if check_bound(self.rect) != (True, True):
            self.kill()        


class BossHPBar:
    """
    画面上部にボスのHPバーを表示するクラス
    """
    def __init__(self,boss:Boss) -> None:
        """
        「BOSS」の文字とバーの位置を用意する
        引数 boss：HPを表示するボス
        """
        self.boss=boss
        self.txt=pg.font.Font(None,30)
        self.label = self.txt.render("BOSS", True, (255, 255, 255))
        self.bar_left=(WIDTH - BOSS_BAR_WIDTH) // 2

    def draw(self,screen: pg.Surface) -> None:
        """
        灰色の背景，HPの割合の幅のバー（色はフェーズで緑・黄・赤），「BOSS」の文字を描く
        引数 screen：画面Surface
        """
        pg.draw.rect(screen,(80,80,80),(self.bar_left, BOSS_BAR_Y, BOSS_BAR_WIDTH, BOSS_BAR_HEIGHT))
        hp_width = int(BOSS_BAR_WIDTH * self.boss.hp / self.boss.max_hp)
        color = BOSS_BAR_COLORS[self.boss.get_phase()]
        pg.draw.rect(screen, color, (self.bar_left, BOSS_BAR_Y, hp_width, BOSS_BAR_HEIGHT))
        screen.blit(self.label, (self.bar_left - self.label.get_width() - 10, BOSS_BAR_Y))


# ===== 【A】アイテムのクラス（Item）はここに書く =====
class Item(pg.sprite.Sprite):
    """
    アイテムに関するクラス
    """
    colors = {
        "heal": (255, 0, 0),     # 回復アイテムの色（赤）
        "power": (255, 255, 0),  # 威力アップアイテムの色（黄）
        "bonus": (0, 255, 0),    # スコアアイテムの色（緑）
    }

    def __init__(self, kind: str, xy: tuple[int, int]) -> None:
        """
        落ちてくるアイテムのSurfaceを生成する
        引数1 kind：生成するアイテムの種類（"heal", "power", "bonus"）
        引数2 xy：アイテムの出現位置（倒した敵の中心座標）タプル
        """
        super().__init__()
        self.kind = kind  # アイテムの種類を保存
        self.image = pg.Surface((40, 40))   # アイテム描画用の空のSurfaceを作成
        self.image.set_colorkey((0, 0, 0))  # 黒背景を透明化
        
        color = __class__.colors[self.kind]  # クラス変数から該当する種類の色を取得
        
        # ハート型に描画するための座標を計算してリスト化
        points = [(16*math.sin(t/100)**3 + 20,
                -(13*math.cos(t/100) - 5*math.cos(2*t/100) - 2*math.cos(3*t/100) - math.cos(4*t/100)) + 20)
                for t in range(0, 628)]  
        
        pg.draw.polygon(self.image, color, points)  # 取得した色と座標でハートを描画
        self.rect = self.image.get_rect()  # SurfaceからRectを抽出
        self.rect.center = xy  # アイテムの出現位置を設定
    
    def update(self) -> None:
        """
        アイテムを落下速度（ITEM_SPEED）に合わせて下方向に移動させる
        画面から出たらアイテムを削除する
        """
        self.rect.move_ip(0, ITEM_SPEED)  # アイテムが落ちる処理
        if check_bound(self.rect) != (True, True):
            self.kill()  # 画面外行ったら自動的に消える


# ===== 【仙田】自機強化のクラス（PowerUp，SpecialGauge，Special）はここに書く =====
class PowerUp:
    """
    自機のビームの数を増やす・レベルの表示をするクラス
    """
    def __init__(self) -> None:
        """
        PowerUpクラスのイニシャライズ
        属性1: 今の段階
        属性2: 文字表示用のフォント
        """
        self.level: int = 1
        self.fonto: pg.font.Font = pg.font.Font(None, 65)

    def update_level(self, score_value: int) -> None:
        """
        レベルを決めるメソッド
        引数1: スコアの値
        戻り値: なし
        """
        if LEVEL_SCORES[1] <= score_value < LEVEL_SCORES[2]:
            self.level = 2
            
        elif LEVEL_SCORES[2] <= score_value:
            self.level = 3

    def get_angles(self) -> list[int]:
        """
        段階に応じた角度のリストを返す
        戻り値: int型が入るリスト(段階によって要素数異なる)
        """
        if self.level == 1:
            return [0]  # Lv1：正面の1方向
        elif self.level == 2:
            return [-15, 0, 15]  # Lv2：3方向
        elif self.level == 3:
            return [-30, -15, 0, 15, 30]  # Lv3：5方向

    def draw(self, screen: pg.Surface) -> None:
        """
        レベルのblitをする
        引数1: 背景画面
        戻り値: なし
        """
        level_txt = self.fonto.render(f"Lv.{self.level}", True, (255, 255, 255))
        rect = level_txt.get_rect()
        rect.center = 100, HEIGHT-100
        screen.blit(level_txt, rect)


class SpecialGauge:
    """
    必殺技を放つゲージの管理をするクラス
    """
    def __init__(self) -> None:
        """
        イニシャライズ
        属性1: 今のゲージ量(最初は0)
        属性2: 必殺技の使用上限回数(最初はSPECIAL_MAX_USE)
        """
        self.value = 0
        self.uses = SPECIAL_MAX_USE

    def add(self, amount: int) -> None:
        """
        雑魚敵を倒すとゲージがたまる関数
        引数1: ゲージの溜まる量
        戻り値: なし
        """
        if self.value <= GAUGE_MAX:
            self.value = min(self.value + amount, GAUGE_MAX)

    def can_use(self) -> bool:
        """
        必殺技を使えるか判定
        戻り値: 必殺技使用可否の真理値を返す
        """
        if (self.value == GAUGE_MAX) and (self.uses >= 1):
            return True
        return False

    def use(self) -> None:
        """
        必殺技を使用したら、ゲージを0にする。また残り回数を1回減らす
        戻り値: なし
        """
        self.value = 0
        self.uses -= 1

    def draw(self, screen: pg.Surface) -> None:
        """
        ゲージバーを2本screenに貼り付け。bar1は灰色。bar2は黄色。
        引数1: 画面
        戻り値: なし
        """
        colour = ()
        if self.value == GAUGE_MAX:
            colour = (255, 165, 0)  # ゲージ満タン：オレンジ
            skill_available = pg.font.SysFont("meiryoui", 40).render(f"使用可能:{self.uses}", True, colour)
            screen.blit(skill_available, [50, HEIGHT-200])
        elif self.value < GAUGE_MAX:
            colour = (255, 255, 0)  # ゲージ途中：黄色
            fonto = pg.font.SysFont("meiryoui", 40)  # 日本語フォント出力のためにSysFont使用
            use_remaining = fonto.render(f"必殺技残り:{self.uses}", True, (0, 0, 0))
            screen.blit(use_remaining, [50, HEIGHT-200])
        pg.draw.rect(screen, (128, 128, 128), (50, HEIGHT-145, 200, 15))
        pg.draw.rect(screen, colour, (50, HEIGHT-145, (200 * self.value / GAUGE_MAX), 15))


class Special(pg.sprite.Sprite):
    """
    必殺技を放つためのクラス
    """
    def __init__(self) -> None:
        """
        イニシャライズ
        属性1: 継承
        属性2: 白色の画面(半透明)
        """
        super().__init__()
        self.life = SPECIAL_TIME
        self.image = pg.Surface((WIDTH, HEIGHT))
        self.rect = self.image.get_rect()
        self.image.fill((255, 255, 255))
        self.image.set_alpha(128)  # 半透明にする

    def update(self) -> None:
        """
        白色の画面を時間に基づき消去
        """
        self.life -= 1
        if self.life < 0:
            self.kill()


# ===== 【C】雑魚敵のサブクラス（ZigzagEnemy，ChaseEnemy，TankEnemy）と出現用の関数はここに書く =====

class ZigzagEnemy(Enemy):
    """左右に揺れながら降下する敵機"""

    def __init__(self) -> None:
        """敵機の画像と出現位置を設定する"""
        super().__init__()
        center = self.rect.center
        self.image = pg.transform.rotozoom(
            pg.image.load("fig/alien2.png"), 0, 0.8
        )
        self.rect = self.image.get_rect(center=center)
        self.base_x = random.randint(
            ZIGZAG_WIDTH + self.rect.width // 2,
            WIDTH - ZIGZAG_WIDTH - self.rect.width // 2
        )
        self.rect.centerx = self.base_x
        self.count = 0

    def update(self) -> None:
        """sin関数で左右に揺れながら降下する"""
        self.count += 1
        self.rect.centerx = self.base_x + int(ZIGZAG_WIDTH * math.sin(self.count * ZIGZAG_SPEED))
        super().update()


class ChaseEnemy(Enemy):
    """こうかとんを追いかける敵機"""

    def __init__(self, bird: Bird) -> None:
        """追跡するこうかとんを設定する"""
        super().__init__()
        center = self.rect.center
        self.image = pg.transform.rotozoom(
            pg.image.load("fig/alien3.png"), 0, 0.8
        )
        self.rect = self.image.get_rect(center=center)
        self.bird = bird
        self.state = "chase"

    def update(self) -> None:
        """こうかとんの方向に移動する"""
        vx, vy = calc_orientation(self.rect, self.bird.rect)
        self.rect.move_ip(CHASE_SPEED * vx, CHASE_SPEED * vy)


class TankEnemy(Enemy):
    """体力が高い大型の敵機"""

    def __init__(self) -> None:
        """体力と画像の大きさを設定する"""
        super().__init__()
        self.hp = TANK_HP
        center = self.rect.center
        self.image = pg.transform.rotozoom(self.image, 0, 1.5)
        self.rect = self.image.get_rect(center=center)

    def draw_hp(self, screen: pg.Surface) -> None:
        """
        硬い敵の上に体力バーを表示する
        引数 screen：画面Surface
        """
        bar_width = 50  # 体力バーの幅
        bar_height = 6  # 体力バーの高さ

        x = self.rect.centerx - bar_width // 2  # 横方向の位置
        y = self.rect.top - 12  # 敵機の上に表示する

        # 体力バーの背景を描画する
        pg.draw.rect(screen, (100, 100, 100),(x, y, bar_width, bar_height))

        # 残り体力に応じてバーの長さを変更する
        hp_width = int(bar_width * max(0, self.hp) / TANK_HP)

        # 残り体力を緑色で表示する
        pg.draw.rect(screen, (0, 255, 0),(x, y, hp_width, bar_height))


def get_spawn_interval(score_value: int) -> int:
    """スコアに応じて敵機の出現間隔を返す"""
    if score_value >= SPAWN_SCORES[2]:
        return SPAWN_INTERVALS[2]
    elif score_value >= SPAWN_SCORES[1]:
        return SPAWN_INTERVALS[1]
    return SPAWN_INTERVALS[0]

def get_fire_interval(score_value: int) -> int:
    """
    スコアに応じて爆弾の投下間隔を返す
    引数 score_value：現在のスコア
    戻り値：爆弾の投下間隔
    """
    if score_value >= SPAWN_SCORES[2]:
        return FIRE_INTERVALS[2]  # 300点以上

    elif score_value >= SPAWN_SCORES[1]:
        return FIRE_INTERVALS[1]  # 100点以上

    return FIRE_INTERVALS[0]  # 100点未満


def get_bomb_speed(score_value: int) -> int:
    """
    スコアに応じて爆弾の移動速度を返す
    引数 score_value：現在のスコア
    戻り値：爆弾の移動速度
    """
    if score_value >= SPAWN_SCORES[2]:
        return BOMB_SPEEDS[2]  # 速度10

    elif score_value >= SPAWN_SCORES[1]:
        return BOMB_SPEEDS[1]  # 速度8

    return BOMB_SPEEDS[0]  # 速度6


def create_enemy(score_value: int, bird: Bird) -> Enemy:
    """スコアに応じて敵機の種類を選択する"""
    if score_value < SPAWN_SCORES[1]:
        return Enemy()

    elif score_value < SPAWN_SCORES[2]:
        enemy_type = random.choice([Enemy, ZigzagEnemy])
        return enemy_type()

    enemy_type = random.choice([
        "normal", "zigzag", "chase", "tank"
    ])

    if enemy_type == "zigzag":
        return ZigzagEnemy()
    elif enemy_type == "chase":
        return ChaseEnemy(bird)
    elif enemy_type == "tank":
        return TankEnemy()

    return Enemy()



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
    exps = pg.sprite.Group()   # 爆発エフェクト
    emys = pg.sprite.Group()   # 雑魚敵（Enemyのサブクラスも入れる）

    # ゲームの状態："play"（通常）／"boss"（ボス戦）
    # 【D】"title"，"gameover"，"clear"を追加する
    state = "title" #ゲームの状態を管理

    # ===== 【中川】ボス用のGroup（bosses）と変数はここで作る =====
    bosses = pg.sprite.Group()  
    boss_spawned = False 
    hp_bar: BossHPBar | None = None
    # ===== 【A】アイテム用のGroup（items）と威力アップの残り時間はここで作る =====
    items = pg.sprite.Group()  # アイテムを管理するグループ
    item_list = ["heal", "power", "bonus"]  # ランダム抽選用アイテム種類のリスト
    power_timer = 0  # 強化状態の残り時間（フレーム数）

    # ===== 【仙田】PowerUp，SpecialGauge，Special用のGroupはここで作る =====
    power_up = PowerUp()
    special_gauge = SpecialGauge()
    special = pg.sprite.Group()

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
                
                # 【仙田】強化段階の角度ごとにビームを作る形に変える
                for angle in power_up.get_angles():  # 強化段階に応じた角度ごとにビームを作る
                    new_beam = Beam(bird, angle)
                    if power_timer > 0:  # 威力アップ期間中の場合
                        new_beam.power += 1  # 生成したビームの威力を1上げる
                    beams.add(new_beam)  # ビームをグループに追加して発射
                    sound.play_se("beem")
                # 【D】ビームの効果音を鳴らす
            # ===== 【仙田】Xキーで必殺技を発動する処理はここに書く =====
            # ゲージが満タンで残り回数があるとき、Xキーで必殺技を発動する
            if event.type == pg.KEYDOWN and event.key == pg.K_x and special_gauge.can_use():
                for emy in emys:  # 画面上の雑魚敵をすべて爆発させて消す
                    exps.add(Explosion(emy, 100))
                    emy.kill()
                for bomb in bombs:  # 敵の弾もすべて消す
                    exps.add(Explosion(bomb, 50))
                    bomb.kill()
                special.add(Special())
                special_gauge.use()

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
                    bosses.empty() #bossesを空に
                    special_gauge = SpecialGauge() #special_gaugeをリセット
                    special.empty() #specialをリセット
                    boss_spawned = False #boss出現フラグをリセット
                    hp_bar = None #bossのhp_barを削除
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


        # 雑魚敵の出現（通常プレイ中だけ）
        if state == "play":
            interval = get_spawn_interval(score.value)  # スコアに応じて出現間隔を決める

            if tmr % interval == 0:  # 指定されたフレーム間隔で敵機を出現させる
                emys.add(create_enemy(score.value, bird))  # スコアに応じた敵機を生成する

        # スコアがBOSS_SCOREを超えたらボス戦へ
        if state == "play" and score.value >= BOSS_SCORE:
            state = "boss"

        # ===== 【中川】ボスを登場させる処理・ボスの攻撃はここに書く =====
        if state=="boss" and not boss_spawned:
            boss=Boss(bird)
            bosses.add(boss)
            hp_bar=BossHPBar(boss)
            boss_spawned=True
        for boss in bosses:
            li=boss.attack(tmr)
            for b in li:
                bombs.add(b)
            if boss.mode=="dying":
                exps.add(Explosion(boss,100))
                score.value+=BOSS_BONUS
                boss.kill()
                state="clear"
        for emy in emys:
            if emy.state == "stop": # 敵機が停止状態に入ったら，intervalに応じて爆弾投下  
                emy.timer += 1

                if emy.timer >= emy.interval:  # 発射時間になったら
                    speed = get_bomb_speed(score.value)  # スコアに応じて爆弾の速度を変更する
                    bombs.add(Bomb(emy, bird, speed))  # 爆弾を発射する
                    emy.timer = 0  # 発射時間をリセットする

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
                if random.random() < ITEM_DROP_RATE:  # 20%の確率でアイテムドロップ
                    item = random.choice(item_list)  # リストの中からランダムでアイテム種類を選ぶ
                    items.add(Item(item, emy.rect.center))  # 敵の中心座標にアイテムを出現させる
                
                # 【B】必殺技のゲージを溜める
                # 【仙田】必殺技のゲージを溜める
                special_gauge.add(GAUGE_PER_ENEMY)
                # 【D】爆発の効果音を鳴らす
                emy.kill()

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        # ===== 【中川】ビームとボスの当たり判定はここに書く =====
                # ビームと雑魚敵の当たり判定（敵は消さずにダメージを与える）
        for boss, hit_beams in pg.sprite.groupcollide(bosses, beams, False, True).items():
            for beam in hit_beams:
                boss.take_damage(beam.power)
            


        # ===== 【A】こうかとんがアイテムを取ったときの処理はここに書く =====
        for item in pg.sprite.spritecollide(bird, items, True):  # 触れたアイテムを自動的にGroupから削除する
            if item.kind == "heal":  # 回復アイテムを拾った時の処理
                bird.life = min(bird.life + 1, LIFE_MAX)  # 残機を1増やす（上限LIFE_MAXを超えないようにする）
            elif item.kind == "bonus":  # スコアアイテムを拾った時の処理
                score.value += BONUS_SCORE  # 現在のスコアにボーナス分を加算する
            elif item.kind == "power":  # 強化アイテムを拾った時の処理
                power_timer = POWER_TIME  # 強化の残り時間をリセットする
        
        # 威力アップの残り時間の管理
        if power_timer > 0:  # マイナスにならないよう0より大きいときだけ減らす
            power_timer -= 1  # 1フレームにつき1ずつ強化時間を減らす

        # ===== 【C】追いかけ敵の体当たり（こうかとんと雑魚敵の当たり判定）はここに書く =====

        for emy in pg.sprite.spritecollide(bird, emys, False):  # こうかとんと衝突した敵機を調べる
            if isinstance(emy, ChaseEnemy):  # 追いかけ敵の場合だけ処理する
                exps.add(Explosion(emy, 50))  # 衝突した位置に爆発エフェクトを表示する
                bird.change_img(8, screen)  # こうかとんの画像を悲しみ画像に変更する
                bird.life -= 1  # 残機を1減らす
                emy.kill()  # 衝突した追いかけ敵を消す

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
        for emy in emys:
            if isinstance(emy, TankEnemy):  # 硬い敵だけ判定する
                emy.draw_hp(screen)  # 敵機の上に体力バーを表示する
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)

        # ===== 【中川】ボスとHPバーの描画はここに書く =====
        bosses.update()
        bosses.draw(screen)
        if hp_bar is not None and len(bosses)>0:
            hp_bar.draw(screen)
        # ===== 【A】アイテムの描画（items.update，items.draw）はここに書く =====
        items.update()      # アイテムの位置を更新する（落下処理）
        items.draw(screen)  # アイテムを画面に描画する

        # ===== 【仙田】強化段階・ゲージ・必殺技の描画はここに書く =====
        power_up.update_level(score.value)  # スコアに応じてレベルを更新
        power_up.draw(screen)  # レベル表示
        special_gauge.draw(screen)  # ゲージと残り回数の表示
        special.update()  # 必殺技エフェクトの残り時間を減らす
        special.draw(screen)  # 必殺技エフェクトを描画
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