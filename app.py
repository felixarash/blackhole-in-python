
import pygame
import numpy as np
import os
import time as pytime
from pygame.locals import FULLSCREEN, NOFRAME, QUIT, KEYDOWN, K_ESCAPE

os.environ['SDL_VIDEO_CENTERED'] = '1'
pygame.init()
info = pygame.display.Info()
# Use a low rendering resolution for performance
render_width = 200
render_height = 150
width = info.current_w
height = info.current_h
screen = pygame.display.set_mode((width, height), FULLSCREEN | NOFRAME)
clock = pygame.time.Clock()

M = 1.0
Rs = 2.0
ds = 0.1
max_steps = 500
r_inner = 3.0
r_outer = 15.0
fov = 60.0
yaw = 0.0
pitch = 0.0
time = 0.0
dragging = False

# Blackbody RGB approximation
def blackbody_rgb(T):
    T = max(T, 1000.0)
    T = T / 100.0
    r = g = b = 0.0
    if T <= 66:
        r = 255
        g = 99.4708025861 * np.log(T) - 161.1195681661
        if T <= 19:
            b = 0
        else:
            b = 138.5177312231 * np.log(T - 10) - 305.0447927307
    else:
        r = 329.698727446 * (T - 60) ** -0.1332047592
        g = 288.1221695283 * (T - 60) ** -0.0755148498
        b = 255
    r = min(max(r, 0), 255) / 255.0
    g = min(max(g, 0), 255) / 255.0
    b = min(max(b, 0), 255) / 255.0
    return np.array([r, g, b])

# Generate sky texture with stars
tex_height = 360
tex_width = 720
sky_texture = np.zeros((tex_height, tex_width, 3))
num_stars = 2000
for _ in range(num_stars):
    i = np.random.randint(0, tex_height)
    j = np.random.randint(0, tex_width)
    sky_texture[i, j] = [1, 1, 1]

def render():
    print('Starting render...')
    t0 = pytime.time()
    n = render_width * render_height
    h = np.tan(fov * np.pi / 360)
    aspect = render_width / render_height
    u = np.linspace(-h * aspect, h * aspect, render_width)
    v = np.linspace(-h, h, render_height)
    u, v = np.meshgrid(u, v)
    dir_cam = np.array([np.cos(pitch) * np.cos(yaw), np.cos(pitch) * np.sin(yaw), np.sin(pitch)])
    right = np.cross(dir_cam, np.array([0, 0, 1]))
    if np.linalg.norm(right) > 0:
        right /= np.linalg.norm(right)
    else:
        right = np.array([1, 0, 0])
    up = np.cross(right, dir_cam)
    dirs = u[:, :, np.newaxis] * right + v[:, :, np.newaxis] * up + dir_cam
    norms = np.sqrt(np.sum(dirs**2, axis=2))[:, :, np.newaxis]
    dirs /= norms
    dirs = dirs.reshape(n, 3)
    pos = np.tile(-20 * dir_cam, (n, 1))
    color = np.zeros((n, 3))
    active = np.ones(n, dtype=bool)
    previous_z = pos[:, 2].copy()
    for step in range(max_steps):
        active_index = np.where(active)[0]
        if len(active_index) == 0:
            break
        pos_a = pos[active_index]
        dir_a = dirs[active_index]
        pos_a += ds * dir_a
        r_a = np.sqrt(np.sum(pos_a**2, axis=1))
        a_a = - (2 * M / r_a**3)[:, np.newaxis] * pos_a
        dot_a = np.sum(a_a * dir_a, axis=1)
        a_perp_a = a_a - dot_a[:, np.newaxis] * dir_a
        dir_a += ds * a_perp_a
        norms_a = np.sqrt(np.sum(dir_a**2, axis=1))[:, np.newaxis]
        dir_a /= norms_a
        pos[active_index] = pos_a
        dirs[active_index] = dir_a
        current_z_a = pos_a[:, 2]
        crossed_a = (previous_z[active_index] * current_z_a < 0)
        if np.any(crossed_a):
            inter_pos_a = pos_a[crossed_a]
            r_disk_a = np.sqrt(np.sum(inter_pos_a[:, :2]**2, axis=1))
            in_disk_a = (r_disk_a > r_inner) & (r_disk_a < r_outer)
            if np.any(in_disk_a):
                inter_dir_a = dir_a[crossed_a][in_disk_a]
                r_disk_in = r_disk_a[in_disk_a]
                phi = np.atan2(inter_pos_a[in_disk_a, 1], inter_pos_a[in_disk_a, 0])
                omega = np.sqrt(M / r_disk_in**3)
                phi_texture = phi - omega * time
                texture_val = 0.5 + 0.5 * np.sin(20 * phi_texture)
                beta = np.sqrt(M / r_disk_in)
                v_x = -beta * np.sin(phi)
                v_y = beta * np.cos(phi)
                v = np.column_stack((v_x, v_y, np.zeros_like(v_x)))
                cos_theta = np.sum(v * (-inter_dir_a), axis=1) / beta
                gamma = 1 / np.sqrt(1 - beta**2)
                z_doppler = 1 / (gamma * (1 - beta * cos_theta)) - 1
                delta_doppler = 1 / (1 + z_doppler)
                delta_grav = np.sqrt(1 - Rs / r_disk_in)
                delta = delta_doppler * delta_grav
                T_em = 5000 * (r_disk_in / (3 * M)) ** -0.75
                T_obs = T_em * delta
                rgb = np.array([blackbody_rgb(t) for t in T_obs])
                rgb *= texture_val[:, np.newaxis] * delta[:, np.newaxis] ** 3
                crossed_indices = np.where(crossed_a)[0][in_disk_a]
                to_set = active_index[crossed_indices]
                color[to_set] = rgb
                active[to_set] = False
        previous_z[active_index] = current_z_a
        hit_a = r_a < Rs
        if np.any(hit_a):
            to_set = active_index[hit_a]
            color[to_set] = [0, 0, 0]
            active[to_set] = False
    # Set remaining active rays to sky
    active_index = np.where(active)[0]
    if len(active_index) > 0:
        dir_a = dirs[active_index]
        phi = np.atan2(dir_a[:, 1], dir_a[:, 0])
        phi = (phi + 2 * np.pi) % (2 * np.pi)
        theta = np.arccos(dir_a[:, 2])
        j = (phi / (2 * np.pi) * tex_width).astype(int) % tex_width
        i = (theta / np.pi * tex_height).astype(int) % tex_height
        rgb = sky_texture[i, j]
        color[active_index] = rgb
    t1 = pytime.time()
    print(f'Render complete in {t1-t0:.2f} seconds')
    return color.reshape((render_width, render_height, 3))


# Render only once for debugging
color = render()
array = np.clip(color * 255, 0, 255).astype(np.uint8)
surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))
surface = pygame.transform.smoothscale(surface, (width, height))
screen.blit(surface, (0, 0))
pygame.display.flip()

# Wait for quit event
running = True
while running:
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                running = False
pygame.quit()
pygame.quit()