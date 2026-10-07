import pygame
import random

TILE = 40
COLS, ROWS = 20, 15
WALL, FLOOR, CHEST, KEY, TRAP = 0, 1, 2, 3, 4
SPEED = 3

def generate_world():
    grid = [[WALL]*COLS for _ in range(ROWS)]
    rooms = []
    for _ in range(8):
        w = random.randint(3,6)
        h = random.randint(3,5)
        x = random.randint(1, COLS-w-1)
        y = random.randint(1, ROWS-h-1)
        room = pygame.Rect(x, y, w, h)
        overlap = any(room.inflate(2,2).colliderect(r) for r in rooms)
        if not overlap:
            rooms.append(room)
            for ry in range(y, y+h):
                for rx in range(x, x+w):
                    grid[ry][rx] = FLOOR

    for i in range(len(rooms)-1):
        ax, ay = rooms[i].centerx, rooms[i].centery
        bx, by = rooms[i+1].centerx, rooms[i+1].centery
        cx = ax
        while cx != bx:
            grid[ay][cx] = FLOOR
            cx += 1 if bx > cx else -1
        cy = ay
        while cy != by:
            grid[cy][bx] = FLOOR
            cy += 1 if by > cy else -1

    if len(rooms) >= 2:
        cr, ck = rooms[-1], rooms[-2]
        grid[cr.centery][cr.centerx] = CHEST
        grid[ck.centery][ck.centerx] = KEY

    start = rooms[0] if rooms else None
    start_cell = (start.y, start.x) if start else None
    reachable = set()
    if start_cell is not None:
        reachable.add(start_cell)
        pending = [start_cell]
        while pending:
            r, c = pending.pop()
            for nr, nc in ((r-1, c), (r+1, c), (r, c-1), (r, c+1)):
                if (0 <= nr < ROWS and 0 <= nc < COLS
                        and grid[nr][nc] != WALL and (nr, nc) not in reachable):
                    reachable.add((nr, nc))
                    pending.append((nr, nc))
    guard_patrol = find_guard_patrol(grid, start, reachable)
    guard_cells = set(guard_patrol or ())
    trap_positions = [
        (r, c)
        for r, c in sorted(reachable)
        if grid[r][c] == FLOOR and (r, c) != start_cell and (r, c) not in guard_cells
    ]
    for r, c in random.sample(trap_positions, min(5, len(trap_positions))):
        grid[r][c] = TRAP
    return grid, start

def find_guard_patrol(grid, start, reachable=None):
    start_cell = (start.y, start.x) if start else None
    if reachable is None:
        reachable = set()
        if start_cell is not None:
            reachable.add(start_cell)
            pending = [start_cell]
            while pending:
                r, c = pending.pop()
                for nr, nc in ((r-1, c), (r+1, c), (r, c-1), (r, c+1)):
                    if (0 <= nr < ROWS and 0 <= nc < COLS
                            and grid[nr][nc] != WALL and (nr, nc) not in reachable):
                        reachable.add((nr, nc))
                        pending.append((nr, nc))

    target = next(
        ((r, c) for r, row in enumerate(grid) for c, cell in enumerate(row) if cell == CHEST),
        start_cell,
    )
    if target is None:
        return None

    candidates = {
        (r, c) for r, c in reachable
        if grid[r][c] == FLOOR and (r, c) != start_cell
    }
    patrol_pairs = [
        (a, b)
        for a in candidates
        for b in ((a[0]+1, a[1]), (a[0], a[1]+1))
        if b in candidates
    ]
    if not patrol_pairs:
        return None
    return min(
        patrol_pairs,
        key=lambda pair: sum(abs(point[0]-target[0]) + abs(point[1]-target[1]) for point in pair),
    )

COLORS = {
    WALL: (60,50,70),
    FLOOR: (200,190,170),
    CHEST: (200,160,30),
    KEY: (220,220,60),
    TRAP: (170,55,45),
}

class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 28, 28)
        self.color = (60,120,220)
        self.has_key = False

    def move(self, keys, grid, rows, cols):
        dx=dy=0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx=-SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx=SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy=-SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy=SPEED
        self._try_move(dx,0,grid,rows,cols)
        self._try_move(0,dy,grid,rows,cols)

    def _try_move(self, dx, dy, grid, rows, cols):
        new = self.rect.move(dx,dy)
        for px,py in [(new.left,new.top),(new.right-1,new.top),(new.left,new.bottom-1),(new.right-1,new.bottom-1)]:
            c,r=px//TILE,py//TILE
            if not(0<=r<rows and 0<=c<cols) or grid[r][c]==WALL:
                return
        self.rect=new

    def draw(self, screen):
        pygame.draw.ellipse(screen, self.color, self.rect)
        if self.has_key:
            pygame.draw.circle(screen, (220,220,60), (self.rect.right-6, self.rect.top+6), 5)

class Guard:
    def __init__(self, patrol):
        self.points = [
            pygame.Vector2(c*TILE+TILE//2, r*TILE+TILE//2)
            for r, c in patrol
        ]
        self.position = self.points[0].copy()
        self.target_index = 1
        self.speed = 2
        self.rect = pygame.Rect(0, 0, 24, 24)
        self.rect.center = (round(self.position.x), round(self.position.y))

    def update(self):
        target = self.points[self.target_index]
        direction = target - self.position
        distance = direction.length()
        if distance <= self.speed:
            self.position = target.copy()
            self.target_index = 1 - self.target_index
        else:
            self.position += direction.normalize() * self.speed
        self.rect.center = (round(self.position.x), round(self.position.y))

    def draw(self, screen):
        pygame.draw.rect(screen, (20, 70, 45), self.rect.inflate(4, 4), border_radius=5)
        pygame.draw.rect(screen, (40, 210, 100), self.rect, border_radius=4)
        pygame.draw.circle(screen, (245, 255, 220), (self.rect.centerx-5, self.rect.centery-2), 2)
        pygame.draw.circle(screen, (245, 255, 220), (self.rect.centerx+5, self.rect.centery-2), 2)


WIDTH = COLS * TILE
HEIGHT = ROWS * TILE + 50
FPS = 60

class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Treasure Hunt")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 24)
        self.big_font = pygame.font.SysFont("monospace", 40, bold=True)
        self.reset()

    def reset(self):
        self.grid, start = generate_world()
        if start:
            sx = start.x * TILE + 6
            sy = start.y * TILE + 6
        else:
            sx, sy = TILE+6, TILE+6
        self.start_position = (sx, sy)
        self.player = Player(sx, sy)
        patrol = find_guard_patrol(self.grid, start)
        self.guard = Guard(patrol) if patrol else None
        self.won = False
        self.status = "Find the KEY, then the CHEST!"
        self.status_until = None

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r: self.reset()
        return True

    def update(self):
        if self.status_until is not None and pygame.time.get_ticks() >= self.status_until:
            self.status = "Got the key! Find the CHEST!" if self.player.has_key else "Find the KEY, then the CHEST!"
            self.status_until = None
        if self.won: return
        keys = pygame.key.get_pressed()
        self.player.move(keys, self.grid, ROWS, COLS)
        if self.guard:
            self.guard.update()
            if self.player.rect.colliderect(self.guard.rect):
                self.player.rect.topleft = self.start_position
                self.status = "Guard caught you! Back to start!"
                self.status_until = pygame.time.get_ticks() + 2000
                return
        pr = self.player.rect.centery // TILE
        pc = self.player.rect.centerx // TILE
        if 0<=pr<ROWS and 0<=pc<COLS:
            cell = self.grid[pr][pc]
            if cell == TRAP:
                self.player.rect.topleft = self.start_position
                self.status = "Trap! Back to start!"
                self.status_until = pygame.time.get_ticks() + 2000
            elif cell == KEY:
                self.player.has_key = True
                self.grid[pr][pc] = FLOOR
                self.status = "Got the key! Find the CHEST!"
                self.status_until = None
            elif cell == CHEST and self.player.has_key:
                self.won = True
                self.status = "Treasure found!"
                self.status_until = None

    def draw(self):
        self.screen.fill((30,25,40))
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]
                rect = pygame.Rect(c*TILE, r*TILE, TILE, TILE)
                pygame.draw.rect(self.screen, COLORS[cell], rect)
                if cell == KEY:
                    pygame.draw.circle(self.screen, (255,240,60),(c*TILE+TILE//2, r*TILE+TILE//2),10)
                elif cell == CHEST:
                    pygame.draw.rect(self.screen,(180,120,20),rect.inflate(-12,-12),border_radius=4)
                elif cell == TRAP:
                    center = (c*TILE+TILE//2, r*TILE+TILE//2)
                    pygame.draw.line(self.screen, (255,210,100), (center[0]-9,center[1]-9), (center[0]+9,center[1]+9), 4)
                    pygame.draw.line(self.screen, (255,210,100), (center[0]+9,center[1]-9), (center[0]-9,center[1]+9), 4)
        self.player.draw(self.screen)
        if self.guard:
            self.guard.draw(self.screen)
        self.draw_minimap()
        hud = pygame.Rect(0,ROWS*TILE,WIDTH,50)
        pygame.draw.rect(self.screen,(20,20,35),hud)
        st = self.font.render(self.status+"  |  R=Restart", True, (200,200,200))
        self.screen.blit(st,(8,ROWS*TILE+13))
        inventory_slot = pygame.Rect(WIDTH-50, ROWS*TILE+5, 42, 40)
        pygame.draw.rect(self.screen, (35,35,50), inventory_slot)
        pygame.draw.rect(self.screen, (145,145,155), inventory_slot, 2)
        if self.player.has_key:
            key_color = COLORS[KEY]
            key_center = (inventory_slot.x+12, inventory_slot.centery)
            pygame.draw.circle(self.screen, key_color, key_center, 6, 3)
            pygame.draw.line(self.screen, key_color, (key_center[0]+6,key_center[1]),
                             (inventory_slot.right-7,key_center[1]), 4)
            pygame.draw.line(self.screen, key_color, (inventory_slot.right-17,key_center[1]),
                             (inventory_slot.right-17,key_center[1]+5), 3)
            pygame.draw.line(self.screen, key_color, (inventory_slot.right-9,key_center[1]),
                             (inventory_slot.right-9,key_center[1]+5), 3)
        if self.won:
            ov=pygame.Surface((WIDTH,ROWS*TILE),pygame.SRCALPHA)
            ov.fill((0,0,0,140))
            self.screen.blit(ov,(0,0))
            msg=self.big_font.render("TREASURE FOUND!", True,(220,180,30))
            sub=self.font.render("Press R to Play Again",True,(180,180,180))
            self.screen.blit(msg,(WIDTH//2-msg.get_width()//2,ROWS*TILE//2-30))
            self.screen.blit(sub,(WIDTH//2-sub.get_width()//2,ROWS*TILE//2+20))
        pygame.display.flip()

    def draw_minimap(self):
        cell_size = 5
        padding = 6
        map_width = COLS * cell_size
        map_height = ROWS * cell_size
        panel = pygame.Rect(WIDTH-map_width-2*padding-12, 12,
                            map_width+2*padding, map_height+2*padding)
        pygame.draw.rect(self.screen, (20,20,35), panel)
        pygame.draw.rect(self.screen, (185,185,185), panel, 1)

        for r, row in enumerate(self.grid):
            for c, cell in enumerate(row):
                color = (55,48,65) if cell == WALL else (205,195,175)
                rect = pygame.Rect(panel.x+padding+c*cell_size,
                                   panel.y+padding+r*cell_size,
                                   cell_size, cell_size)
                pygame.draw.rect(self.screen, color, rect)

        player_x = panel.x + padding + self.player.rect.centerx * map_width // WIDTH
        player_y = panel.y + padding + self.player.rect.centery * map_height // (ROWS*TILE)
        pygame.draw.circle(self.screen, (20,20,20), (player_x,player_y), 4)
        pygame.draw.circle(self.screen, (50,220,255), (player_x,player_y), 2)

    def run(self):
        running=True
        while running:
            running=self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    engine = GameEngine()
    engine.run()
