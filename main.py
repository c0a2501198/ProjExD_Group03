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
ITEM_DROP_RATE = 0.2  # アイテムが出る確率（20%）
ITEM_SPEED = 3        # アイテムが落ちる速さ
LIFE_MAX = 5          # 回復したときの残機の上限
POWER_TIME = 500      # 威力アップが続くフレーム数（約10秒）
BONUS_SCORE = 30      # スコアアイテムで増える点数
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
        
        # ハート型に描画するための座標（媒介変数表示）を計算してリスト化
        points = [(16*math.sin(t/100)**3 + 20,
                -(13*math.cos(t/100) - 5*math.cos(2*t/100) - 2*math.cos(3*t/100) - math.cos(4*t/100)) + 20)
                for t in range(0, 628)]  
        
        pg.draw.polygon(self.image, color, points)  # 取得した色と座標でハートを描画
        self.rect = self.image.get_rect()  # SurfaceからRectを抽出
        self.rect.center = xy  # アイテムの出現位置を設定
    
    def update(self) -> None:
        """
        アイテムを落下速度（ITEM_SPEED）に合わせて下方向に移動させる
        画面から完全に出たらアイテムを削除する
        """
        self.rect.move_ip(0, ITEM_SPEED)  # アイテムが落ちる処理
        if check_bound(self.rect) != (True, True):
            self.kill()  # 画面外行ったら自動的に消える


# ===== 【B】自機強化のクラス（PowerUp，SpecialGauge，Special）はここに書く =====


# ===== 【C】雑魚敵のサブクラス（ZigzagEnemy，ChaseEnemy，TankEnemy）と出現用の関数はここに書く =====


# ===== 【D】画面遷移・サウンドのクラス（TitleScreen，ResultScreen，SoundManager）はここに書く =====


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
    state = "play"

    # ===== 【中川】ボス用のGroup（bosses）と変数はここで作る =====

    # ===== 【A】アイテム用のGroup（items）と威力アップの残り時間はここで作る =====
    items = pg.sprite.Group()  # アイテムを管理するグループ
    item_list = ["heal", "power", "bonus"]  # ランダム抽選用アイテム種類のリスト
    power_timer = 0  # 強化状態の残り時間（フレーム数）

    # ===== 【B】PowerUp，SpecialGauge，Special用のGroupはここで作る =====

    # ===== 【D】TitleScreen，ResultScreen，SoundManagerはここで作る =====

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                # 【A】威力アップ中は作ったビームのpowerを+1する
                new_beam = Beam(bird)
                if power_timer > 0:  # 威力アップ期間中の場合
                    new_beam.power += 1  # 生成したビームの威力を1上げる
                beams.add(new_beam)  # ビームをグループに追加して発射
                
                # 【B】強化段階の角度ごとにビームを作る形に変える
                # 【D】ビームの効果音を鳴らす

            # ===== 【B】Xキーで必殺技を発動する処理はここに書く =====

            # ===== 【D】Enterキーでスタート・リトライする処理はここに書く =====

        # ===== 【D】タイトル画面・結果画面を描いてcontinueする処理はここに書く =====

        # ===== 【D】stateに合わせてBGMを切り替える処理はここに書く =====

        screen.blit(bg_img, [0, 0])

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
                if random.random() < ITEM_DROP_RATE:  # 20%の確率でアイテムドロップ
                    item = random.choice(item_list)  # リストの中からランダムでアイテム種類を選ぶ
                    items.add(Item(item, emy.rect.center))  # 敵の中心座標にアイテムを出現させる
                
                # 【B】必殺技のゲージを溜める
                # 【D】爆発の効果音を鳴らす
                emy.kill()

        for bomb in pg.sprite.groupcollide(bombs, beams, True, False).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        # ===== 【中川】ビームとボスの当たり判定はここに書く =====

        # ===== 【A】こうかとんがアイテムを取ったときの処理はここに書く =====
        # spritecollideの第3引数をTrueにすることで、触れたアイテムは自動的にGroupから削除される
        for item in pg.sprite.spritecollide(bird, items, True): 
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

        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))
            bird.change_img(8, screen)  # こうかとん悲しみエフェクト
            bird.life -= 1
            # 【D】被弾の効果音を鳴らす

        if bird.life <= 0:
            # 【D】ここをstate = "gameover"にする（今はゲームを終了する）
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return

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
        items.update()      # アイテムの位置を更新する（落下処理）
        items.draw(screen)  # アイテムを画面に描画する

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