import math
import tkinter as tk
from tkinter import ttk


class FirstPersonVolleyballSim:
    def __init__(self, root):
        self.root = root
        self.root.title("First-Person 3D Volleyball Simulator")
        self.root.configure(bg="#111827")
        self.root.resizable(False, False)

        # Physics & Space Dimensions (Meters)
        self.ball_radius = 0.105

        self.ball = {
            "x": 0.0, "y": 0.11, "z": -2.5,
            "vx": 0.0, "vy": 0.0, "vz": 0.0
        }
        self.ball_rot_x = 0.0
        self.ball_rot_y = 0.0
        self.running = False
        self.dt = 0.016
        self.dragging_ball = False
        self.player_x = 0.0
        self.player_z = -4.2
        self.player_speed = 3.5
        self.keys_pressed = set()
        self.camera_mode = "first_person"
        self.camera_toggle_label = None
        self.camera_pitch = 0.0
        self.camera_yaw = 0.0
        self.player_walk_phase = 0.0
        self.npc_left = {"x": -2.2, "z": 3.2, "phase": 0.0}
        self.npc_right = {"x": 2.2, "z": 3.8, "phase": 0.0}
        self.npc_cooldown = 0.0
        self.rally_touch_count = 0
        self.last_touch_by = None

        # First-Person Camera Configuration
        self.cam_x = 0.0
        self.cam_y = 1.25
        self.cam_z = -0.4
        self.focal_length = 900
        self.center_x = 425
        self.center_y = 315

        # UI Control Variables
        self.gravity_var = tk.DoubleVar(value=9.81)
        self.air_drag_var = tk.DoubleVar(value=0.25)
        self.elasticity_var = tk.DoubleVar(value=0.75)
        
        self.speed_var = tk.DoubleVar(value=18.0)
        self.elev_var = tk.DoubleVar(value=20.0)    
        self.azim_var = tk.DoubleVar(value=0.0)     
        
        self.spin_speed_var = tk.DoubleVar(value=30.0)
        self.spin_type_var = tk.StringVar(value="Topspin")
        
        self.pos_x_var = tk.StringVar(value="0.0")
        self.pos_y_var = tk.StringVar(value="2.5")
        self.pos_z_var = tk.StringVar(value="-9.0")
        self.status_var = tk.StringVar(value="Ready")

        self.root.bind("<KeyPress>", self.handle_key_press)
        self.root.bind("<KeyRelease>", self.handle_key_release)
        self.build_ui()
        self.spawn_ball_in_front_of_player()
        self.render_scene()
        self.animate()

    def rotate_vector_for_camera(self, dx, dy, dz):
        pitch = self.camera_pitch
        yaw = self.camera_yaw

        rotated_dy = dy * math.cos(pitch) - dz * math.sin(pitch)
        rotated_dz = dy * math.sin(pitch) + dz * math.cos(pitch)

        rotated_dx = dx * math.cos(yaw) + rotated_dz * math.sin(yaw)
        rotated_dz = -dx * math.sin(yaw) + rotated_dz * math.cos(yaw)
        return rotated_dx, rotated_dy, rotated_dz

    def project_3d_to_2d(self, x, y, z):
        """Perspective projection with a simple camera pitch and yaw."""
        dx = x - self.cam_x
        dy = y - self.cam_y
        dz = z - self.cam_z
        dx, dy, dz = self.rotate_vector_for_camera(dx, dy, dz)

        if dz < 0.1:
            dz = 0.1

        px = self.center_x + (dx * self.focal_length) / dz
        py = self.center_y - (dy * self.focal_length) / dz
        return px, py, dz

    def inverse_project_floor(self, screen_x, screen_y):
        """Casts a ray from the camera through the 2D screen to find the 3D floor (Y=0)."""
        dy = self.center_y - screen_y
        if dy >= 0:
            return None, None # Clicked above the horizon
            
        # Extrapolate depth (dz) based on camera height and screen Y
        # Formula derived from: screen_y = center_y - ((world_y - cam_y) * f) / dz
        # Setting world_y = 0 (floor)
        dz = (self.cam_y * self.focal_length) / -dy
        z_world = self.cam_z + dz
        
        dx = screen_x - self.center_x
        x_world = self.cam_x + (dx * dz) / self.focal_length
        
        return x_world, z_world

    def build_ui(self):
        main_frame = tk.Frame(self.root, bg="#111827")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 3D Canvas
        self.canvas = tk.Canvas(
            main_frame, width=850, height=580, bg="#1f2937", highlightthickness=0
        )
        self.canvas.pack(side="left", padx=(0, 10))
        self.canvas.bind("<Button-1>", self.handle_canvas_click)
        self.canvas.bind("<B1-Motion>", self.handle_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.handle_canvas_release)

        # Control Panel
        sidebar = tk.Frame(main_frame, bg="#1f2937", padx=15, pady=15, width=280)
        sidebar.pack(side="right", fill="y")
        sidebar.pack_propagate(False)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", foreground="#e2e8f0", background="#1f2937", font=("Segoe UI", 9))

        tk.Label(sidebar, text="ENVIRONMENT", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#1f2937").pack(anchor="w", pady=(0, 4))
        self.create_slider(sidebar, "Gravity", self.gravity_var, 0.0, 20.0)
        self.create_slider(sidebar, "Drag", self.air_drag_var, 0.0, 1.0)
        self.create_slider(sidebar, "Bounce", self.elasticity_var, 0.1, 0.95)

        tk.Label(sidebar, text="LAUNCH CONFIG", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#1f2937").pack(anchor="w", pady=(10, 4))
        self.create_slider(sidebar, "Speed", self.speed_var, 5.0, 40.0)
        self.create_slider(sidebar, "Elevation", self.elev_var, -10.0, 80.0)
        self.create_slider(sidebar, "Angle (L/R)", self.azim_var, -45.0, 45.0)

        tk.Label(sidebar, text="SPIN EFFECT", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#1f2937").pack(anchor="w", pady=(10, 4))
        self.create_slider(sidebar, "Spin Rate", self.spin_speed_var, 0.0, 80.0)
        ttk.Combobox(sidebar, textvariable=self.spin_type_var, values=["Topspin", "Backspin", "Left Sidespin", "Right Sidespin"], state="readonly").pack(fill="x", pady=4)

        btn_frame = tk.Frame(sidebar, bg="#1f2937")
        btn_frame.pack(fill="x", pady=15)
        ttk.Button(btn_frame, text="Serve Ball", command=self.launch_ball).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Pause/Resume", command=self.toggle_pause).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Reset", command=self.reset_ball).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Switch Camera", command=self.toggle_camera_mode).pack(fill="x", pady=2)

        self.telemetry_label = tk.Label(
            sidebar, text="", font=("Consolas", 9), fg="#a7f3d0", bg="#111827",
            justify="left", anchor="w", relief="sunken", bd=1, padx=6, pady=6
        )
        self.telemetry_label.pack(fill="both", expand=True, pady=(5, 0))

        tk.Label(
            sidebar,
            text="Drag the ball to reposition it. Use W/A/S/D to move and arrow keys to look up/down.",
            font=("Segoe UI", 9),
            fg="#fde68a",
            bg="#1f2937",
            justify="left",
            wraplength=250,
        ).pack(anchor="w", pady=(4, 0))

    def create_slider(self, parent, label, variable, from_val, to_val):
        frame = tk.Frame(parent, bg="#1f2937")
        frame.pack(fill="x", pady=2)
        ttk.Label(frame, text=label).pack(side="left")
        ttk.Scale(frame, from_=from_val, to_=to_val, variable=variable, orient="horizontal").pack(side="right", fill="x", expand=True, padx=(5, 0))

    def draw_prism(self, cx, cy, cz, dx, dy, dz, c_top, c_front, c_side):
        """Builds a solid 3D block sorting the 6 faces dynamically for perspective viewing."""
        x0, x1 = cx - dx/2, cx + dx/2
        y0, y1 = cy, cy + dy
        z0, z1 = cz - dz/2, cz + dz/2

        # 8 Corners
        verts = {
            'blf': (x0, y0, z0), 'brf': (x1, y0, z0), 'trf': (x1, y1, z0), 'tlf': (x0, y1, z0),
            'blb': (x0, y0, z1), 'brb': (x1, y0, z1), 'trb': (x1, y1, z1), 'tlb': (x0, y1, z1)
        }
        
        # Map to 2D
        p = {k: self.project_3d_to_2d(*v)[:2] for k, v in verts.items()}
        
        faces = [
            # ID, Vertices, Color, Center Depth (Z)
            ('front', [p['blf'], p['brf'], p['trf'], p['tlf']], c_front, z0),
            ('back',  [p['brb'], p['blb'], p['tlb'], p['trb']], c_front, z1),
            ('left',  [p['blb'], p['blf'], p['tlf'], p['tlb']], c_side, cz),
            ('right', [p['brf'], p['brb'], p['trb'], p['trf']], c_side, cz),
            ('top',   [p['tlf'], p['trf'], p['trb'], p['tlb']], c_top, cz),
            ('bottom',[p['blb'], p['brb'], p['brf'], p['blf']], c_front, cz)
        ]
        
        # Sort faces from back to front
        faces.sort(key=lambda face: face[3], reverse=True)
        
        for name, poly, color, depth in faces:
            self.canvas.create_polygon(poly, fill=color, outline="#111827", width=1)

    def render_scene(self):
        self.canvas.delete("all")

        # Sky and distant backdrop
        self.canvas.create_rectangle(0, 0, 850, 580, fill="#071426", outline="")
        self.canvas.create_rectangle(0, 0, 850, 260, fill="#0f4c81", outline="")
        self.canvas.create_rectangle(0, 260, 850, 580, fill="#111827", outline="")
        self.canvas.create_line(0, 260, 850, 260, fill="#bae6fd", width=2)

        backdrop = [
            self.project_3d_to_2d(-16, 0, -14)[:2],
            self.project_3d_to_2d(16, 0, -14)[:2],
            self.project_3d_to_2d(16, 12, -14)[:2],
            self.project_3d_to_2d(-16, 12, -14)[:2],
        ]
        self.canvas.create_polygon(backdrop, fill="#1e3a5f", outline="", smooth=False)

        # Court floor and raised perimeter
        floor_corners = [
            (-6.3, 0.0, -10.2),
            (6.3, 0.0, -10.2),
            (6.3, 0.0, 10.2),
            (-6.3, 0.0, 10.2),
        ]
        floor_poly = [self.project_3d_to_2d(*pt)[:2] for pt in floor_corners]
        self.canvas.create_polygon(floor_poly, fill="#e7c36b", outline="#ffffff", width=3, smooth=False)

        raised_edge = [
            (-6.6, 0.02, -10.5),
            (6.6, 0.02, -10.5),
            (6.6, 0.02, 10.5),
            (-6.6, 0.02, 10.5),
        ]
        raised_poly = [self.project_3d_to_2d(*pt)[:2] for pt in raised_edge]
        self.canvas.create_polygon(raised_poly, fill="#b68a2d", outline="#ffffff", width=2, smooth=False)

        # Court side walls to make the arena feel volumetric
        wall_left = [
            (-6.6, 0.02, -10.5),
            (-6.6, 0.02, 10.5),
            (-6.6, 3.2, 10.5),
            (-6.6, 3.2, -10.5),
        ]
        wall_right = [
            (6.6, 0.02, -10.5),
            (6.6, 0.02, 10.5),
            (6.6, 3.2, 10.5),
            (6.6, 3.2, -10.5),
        ]
        self.canvas.create_polygon([self.project_3d_to_2d(*pt)[:2] for pt in wall_left], fill="#3b4a66", outline="#dbeafe", width=1)
        self.canvas.create_polygon([self.project_3d_to_2d(*pt)[:2] for pt in wall_right], fill="#3b4a66", outline="#dbeafe", width=1)

        back_wall = [
            (-6.6, 0.02, 10.5),
            (6.6, 0.02, 10.5),
            (6.6, 3.2, 10.5),
            (-6.6, 3.2, 10.5),
        ]
        self.canvas.create_polygon([self.project_3d_to_2d(*pt)[:2] for pt in back_wall], fill="#243447", outline="#f8fafc", width=1)

        # Court markings
        def draw_line(lx1, lz1, lx2, lz2, y=0.02):
            self.canvas.create_line(
                *self.project_3d_to_2d(lx1, y, lz1)[:2],
                *self.project_3d_to_2d(lx2, y, lz2)[:2],
                fill="#ffffff",
                width=2,
            )

        draw_line(-4.5, -9.0, 4.5, -9.0)
        draw_line(-4.5, 9.0, 4.5, 9.0)
        draw_line(-4.5, 0.0, 4.5, 0.0)
        draw_line(-4.5, -3.0, 4.5, -3.0)
        draw_line(-4.5, 3.0, 4.5, 3.0)

        render_queue = []

        # Benches and stadium seating
        for bx, bz in [(6.8, 4.2), (6.8, -4.2), (-6.8, 4.2), (-6.8, -4.2)]:
            dist = math.hypot(bx - self.cam_x, 0.0 - self.cam_y, bz - self.cam_z)
            render_queue.append({"depth": dist, "func": lambda x=bx, z=bz: self.draw_bench(x, z)})

        # Net and posts
        net_dist = math.hypot(0 - self.cam_x, 1.2 - self.cam_y, 0 - self.cam_z)
        render_queue.append({"depth": net_dist, "func": self.draw_net})

        # Player and NPCs
        render_queue.append({"depth": 999, "func": self.draw_player})
        render_queue.append({"depth": 998, "func": self.draw_npc_left})
        render_queue.append({"depth": 997, "func": self.draw_npc_right})

        # Ball
        ball_dist = math.hypot(self.ball["x"] - self.cam_x, self.ball["y"] - self.cam_y, self.ball["z"] - self.cam_z)
        render_queue.append({"depth": ball_dist, "func": self.draw_ball})

        render_queue.sort(key=lambda item: item["depth"], reverse=True)
        for item in render_queue:
            item["func"]()

        self.canvas.create_text(425, 25, text=self.status_var.get().upper(), fill="#ffffff", font=("Segoe UI", 12, "bold"))

    def draw_bench(self, x, z):
        """Draws a 3D wooden bench."""
        self.draw_prism(x, 0, z-0.8, 0.15, 0.4, 0.15, "#2a1a0f", "#1e130a", "#4a2e1b") # Leg 1
        self.draw_prism(x, 0, z+0.8, 0.15, 0.4, 0.15, "#2a1a0f", "#1e130a", "#4a2e1b") # Leg 2
        self.draw_prism(x, 0.4, z, 0.4, 0.05, 2.0, "#cf995f", "#8b6339", "#a67848")   # Wooden Top

    def draw_net(self):
        """Renders a bright white net and posts in perspective."""
        self.draw_prism(-5.1, 0, 0, 0.15, 1.2, 0.15, "#f8fafc", "#e2e8f0", "#ffffff")
        self.draw_prism(-5.1, 1.2, 0, 0.16, 0.5, 0.16, "#0f172a", "#111827", "#1e293b")
        self.draw_prism(-5.1, 1.7, 0, 0.15, 0.8, 0.15, "#f8fafc", "#e2e8f0", "#ffffff")

        self.draw_prism(5.1, 0, 0, 0.15, 1.2, 0.15, "#f8fafc", "#e2e8f0", "#ffffff")
        self.draw_prism(5.1, 1.2, 0, 0.16, 0.5, 0.16, "#0f172a", "#111827", "#1e293b")
        self.draw_prism(5.1, 1.7, 0, 0.15, 0.8, 0.15, "#f8fafc", "#e2e8f0", "#ffffff")

        tp_l, tp_r = self.project_3d_to_2d(-5.1, 2.43, 0)[:2], self.project_3d_to_2d(5.1, 2.43, 0)[:2]
        bt_l, bt_r = self.project_3d_to_2d(-5.1, 1.43, 0)[:2], self.project_3d_to_2d(5.1, 1.43, 0)[:2]

        self.canvas.create_polygon([tp_l, tp_r, bt_r, bt_l], fill="", outline="#ffffff", width=3)
        self.canvas.create_line(*tp_l, *tp_r, fill="#ffffff", width=4)

        for i in range(1, 4):
            hl_l, hl_r = self.project_3d_to_2d(-5.1, 2.43 - i * 0.25, 0)[:2], self.project_3d_to_2d(5.1, 2.43 - i * 0.25, 0)[:2]
            self.canvas.create_line(*hl_l, *hl_r, fill="#ffffff", width=2, stipple="gray50")
        for j in range(1, 25):
            vl_t, vl_b = self.project_3d_to_2d(-5.1 + j * 0.4, 2.43, 0)[:2], self.project_3d_to_2d(-5.1 + j * 0.4, 1.43, 0)[:2]
            self.canvas.create_line(*vl_t, *vl_b, fill="#ffffff", width=1, stipple="gray50")

    def draw_player(self):
        self.draw_character(self.player_x, self.player_z, "#38bdf8", self.player_walk_phase, 1.0)

    def draw_npc_left(self):
        self.draw_character(self.npc_left["x"], self.npc_left["z"], "#f59e0b", self.npc_left["phase"], -1.0)

    def draw_npc_right(self):
        self.draw_character(self.npc_right["x"], self.npc_right["z"], "#22c55e", self.npc_right["phase"], 1.0)

    def draw_character(self, x, z, color, walk_phase, facing):
        px, py, _ = self.project_3d_to_2d(x, 0.9, z)
        bob = math.sin(walk_phase) * 2.5
        leg_swing = math.sin(walk_phase * 1.6) * 6.0 * facing
        arm_swing = math.sin(walk_phase * 1.6 + 0.7) * 5.0 * facing

        self.canvas.create_oval(px - 6, py - 6 + bob, px + 6, py + 6 + bob, fill=color, outline="#0f172a", width=1)
        self.canvas.create_line(px, py + 6 + bob, px, py + 22 + bob, fill=color, width=3)
        self.canvas.create_line(px, py + 12 + bob, px + leg_swing, py + 28 + bob, fill=color, width=3)
        self.canvas.create_line(px, py + 12 + bob, px - leg_swing * 0.6, py + 28 + bob, fill=color, width=3)
        self.canvas.create_line(px, py + 12 + bob, px + arm_swing, py + 20 + bob, fill=color, width=3)
        self.canvas.create_line(px, py + 12 + bob, px - arm_swing * 0.8, py + 20 + bob, fill=color, width=3)
        self.canvas.create_line(px, py + 22 + bob, px + 8 * facing, py + 34 + bob, fill=color, width=3)
        self.canvas.create_line(px, py + 22 + bob, px - 8 * facing, py + 34 + bob, fill=color, width=3)

    def draw_ball(self):
        bx, by, bz = self.ball["x"], self.ball["y"], self.ball["z"]
        px, py, pz = self.project_3d_to_2d(bx, by, bz)
        sh_x, sh_y, sh_z = self.project_3d_to_2d(bx, 0.01, bz)

        # Dynamically scale radius based on perspective depth (Z distance)
        r = (self.ball_radius * self.focal_length) / pz
        shadow_r = (self.ball_radius * self.focal_length) / sh_z
        
        # Render Ground Shadow
        self.canvas.create_oval(sh_x - shadow_r, sh_y - shadow_r*0.4, 
                                sh_x + shadow_r, sh_y + shadow_r*0.4, 
                                fill="#111827", outline="", stipple="gray50")

        # Main Yellow Ball Body
        self.canvas.create_oval(px - r, py - r, px + r, py + r, fill="#ffd700", outline="#000000", width=1)
        
        # 3D Highlight Shine
        self.canvas.create_oval(px - r*0.5, py - r*0.5, px + r*0.2, py + r*0.2, fill="#ffffff", outline="")

        # Seam Rotations Mapping
        s1_x = math.cos(self.ball_rot_x) * r * 0.9
        s1_y = math.sin(self.ball_rot_x) * r * 0.9
        s2_x = math.cos(self.ball_rot_y) * r * 0.9
        s2_y = math.sin(self.ball_rot_y) * r * 0.9

        self.canvas.create_line(px - s1_x, py - s1_y, px + s1_x, py + s1_y, fill="#1b2845", width=max(1, int(r*0.1)))
        self.canvas.create_line(px - s2_y, py + s2_x, px + s2_y, py - s2_x, fill="#ffffff", width=max(1, int(r*0.1)))

    def handle_key_press(self, event):
        self.keys_pressed.add(event.keysym.lower())

    def handle_key_release(self, event):
        self.keys_pressed.discard(event.keysym.lower())

    def update_player_movement(self):
        forward = 1 if "w" in self.keys_pressed else 0
        backward = 1 if "s" in self.keys_pressed else 0
        left = 1 if "a" in self.keys_pressed else 0
        right = 1 if "d" in self.keys_pressed else 0

        moving = bool(forward or backward or left or right)
        if moving:
            step = self.player_speed * self.dt
            self.player_x += (right - left) * step
            self.player_z += (forward - backward) * step
            self.player_x = max(-4.2, min(4.2, self.player_x))
            self.player_z = max(-5.0, min(-1.2, self.player_z))

        if self.camera_mode == "first_person":
            self.cam_x = self.player_x
            self.cam_z = self.player_z - 0.05
            self.cam_y = 1.35
        else:
            self.cam_x = self.player_x
            self.cam_z = self.player_z - 2.9
            self.cam_y = 2.2

        if moving:
            self.player_walk_phase += self.dt * 8.0
        else:
            self.player_walk_phase = max(0.0, self.player_walk_phase - self.dt * 2.0)

        self.npc_left["phase"] += self.dt * 3.2
        self.npc_right["phase"] += self.dt * 3.2

    def update_camera_controls(self):
        has_vertical = "up" in self.keys_pressed or "down" in self.keys_pressed
        has_horizontal = "left" in self.keys_pressed or "right" in self.keys_pressed

        if has_vertical and not has_horizontal:
            if "up" in self.keys_pressed:
                self.camera_pitch = min(0.75, self.camera_pitch + 0.03)
            if "down" in self.keys_pressed:
                self.camera_pitch = max(-0.75, self.camera_pitch - 0.03)
        elif has_horizontal and not has_vertical:
            if "left" in self.keys_pressed:
                self.camera_yaw = max(-0.8, self.camera_yaw - 0.025)
            if "right" in self.keys_pressed:
                self.camera_yaw = min(0.8, self.camera_yaw + 0.025)

    def spawn_ball_in_front_of_player(self):
        self.ball = {
            "x": self.player_x,
            "y": 0.11,
            "z": self.player_z + 1.0,
            "vx": 0.0,
            "vy": 0.0,
            "vz": 0.0,
        }
        self.ball_rot_x = 0.0
        self.ball_rot_y = 0.0
        self.running = False
        self.dragging_ball = False
        self.rally_touch_count = 0
        self.last_touch_by = None

    def perform_npc_touch(self, npc_key, npc_data, action):
        if npc_key == "left":
            target = self.npc_right
            target_x = target["x"]
            target_z = target["z"] - 0.8
        else:
            target = self.npc_left
            target_x = target["x"]
            target_z = target["z"] + 0.8

        if action == "bump":
            self.ball["vx"] = (target_x - self.ball["x"]) * 0.75
            self.ball["vy"] = 0.55
            self.ball["vz"] = (target_z - self.ball["z"]) * 0.6 + 2.2
        elif action == "set":
            self.ball["vx"] = (target_x - self.ball["x"]) * 0.45
            self.ball["vy"] = 1.35
            self.ball["vz"] = (target_z - self.ball["z"]) * 0.7 + 3.2
        elif action == "spike":
            self.ball["vx"] = (self.player_x - self.ball["x"]) * 0.35
            self.ball["vy"] = 0.25
            self.ball["vz"] = 7.5 if npc_key == "left" else 8.0

        self.ball["y"] = 0.11
        self.last_touch_by = npc_key
        self.npc_cooldown = 0.9

    def update_npc_rally(self):
        self.npc_cooldown = max(0.0, self.npc_cooldown - self.dt)
        if self.npc_cooldown > 0.0:
            return

        if not self.running:
            return

        near_left = abs(self.ball["x"] - self.npc_left["x"]) < 1.6 and abs(self.ball["z"] - self.npc_left["z"]) < 2.4
        near_right = abs(self.ball["x"] - self.npc_right["x"]) < 1.6 and abs(self.ball["z"] - self.npc_right["z"]) < 2.4

        if self.ball["y"] < 1.2 and self.ball["z"] > 0.0 and near_left and self.last_touch_by != "left":
            if self.rally_touch_count % 3 == 0:
                action = "bump"
            elif self.rally_touch_count % 3 == 1:
                action = "set"
            else:
                action = "spike"
            self.perform_npc_touch("left", self.npc_left, action)
            self.rally_touch_count += 1
            self.status_var.set(f"Left NPC {action}s")
        elif self.ball["y"] < 1.2 and self.ball["z"] > 0.0 and near_right and self.last_touch_by != "right":
            if self.rally_touch_count % 3 == 0:
                action = "bump"
            elif self.rally_touch_count % 3 == 1:
                action = "set"
            else:
                action = "spike"
            self.perform_npc_touch("right", self.npc_right, action)
            self.rally_touch_count += 1
            self.status_var.set(f"Right NPC {action}s")

        if self.rally_touch_count >= 3:
            self.rally_touch_count = 0
            self.last_touch_by = None

    def update_physics(self):
        self.update_player_movement()
        self.update_camera_controls()
        self.update_npc_rally()

        g = self.gravity_var.get()
        drag = self.air_drag_var.get()
        spin = self.spin_speed_var.get()
        spin_type = self.spin_type_var.get()
        v_mag = math.hypot(self.ball["vx"], self.ball["vy"], self.ball["vz"])

        # Aerodynamic Drag
        ax = -drag * 0.15 * v_mag * self.ball["vx"]
        ay = -g - (drag * 0.15 * v_mag * self.ball["vy"])
        az = -drag * 0.15 * v_mag * self.ball["vz"]

        # Magnus Effect (Spin Curve)
        wx, wy, wz = 0.0, 0.0, 0.0
        if spin_type == "Topspin": wx = -spin
        elif spin_type == "Backspin": wx = spin
        elif spin_type == "Left Sidespin": wy = spin
        elif spin_type == "Right Sidespin": wy = -spin

        cm = 0.025 
        ax += cm * (wy * self.ball["vz"] - wz * self.ball["vy"])
        ay += cm * (wz * self.ball["vx"] - wx * self.ball["vz"])
        az += cm * (wx * self.ball["vy"] - wy * self.ball["vx"])

        self.ball["vx"] += ax * self.dt
        self.ball["vy"] += ay * self.dt
        self.ball["vz"] += az * self.dt

        prev_x, prev_y, prev_z = self.ball["x"], self.ball["y"], self.ball["z"]

        self.ball["x"] += self.ball["vx"] * self.dt
        self.ball["y"] += self.ball["vy"] * self.dt
        self.ball["z"] += self.ball["vz"] * self.dt

        self.ball_rot_x += wx * self.dt
        self.ball_rot_y += wy * self.dt + 0.1 * self.ball["vz"] * self.dt

        # Net Collision Dynamics
        if (prev_z < 0 and self.ball["z"] >= -self.ball_radius) or (prev_z > 0 and self.ball["z"] <= self.ball_radius):
            t = (0.0 - prev_z) / (self.ball["z"] - prev_z) if self.ball["z"] != prev_z else 0.5
            x_hit = prev_x + t * (self.ball["x"] - prev_x)
            y_hit = prev_y + t * (self.ball["y"] - prev_y)

            if abs(x_hit) <= 4.7 and y_hit <= 2.43:
                self.status_var.set("Hit the Net!")
                self.ball["z"] = prev_z
                self.ball["vz"] = -self.ball["vz"] * 0.25
                self.ball["vx"] *= 0.5
                self.ball["vy"] *= 0.5

        # Court Floor Collisions
        if self.ball["y"] - self.ball_radius <= 0.0:
            self.ball["y"] = self.ball_radius
            self.ball["vy"] = -self.ball["vy"] * self.elasticity_var.get()
            self.ball["vx"] *= 0.75
            self.ball["vz"] *= 0.75

            if abs(self.ball["x"]) <= 4.5 and abs(self.ball["z"]) <= 9.0:
                self.status_var.set("In Bounds (Sand)")
            else:
                self.status_var.set("Out of Bounds (Cyan)")

            if abs(self.ball["vy"]) < 0.3 and math.hypot(self.ball["vx"], self.ball["vz"]) < 0.4:
                self.running = False
                self.ball["vx"], self.ball["vy"], self.ball["vz"] = 0.0, 0.0, 0.0

        if abs(self.ball["x"]) > 12.0 or abs(self.ball["z"]) > 16.0:
            self.running = False
            self.status_var.set("Ball exited arena.")

    def animate(self):
        if self.running:
            self.update_physics()
        self.render_scene()
        self.update_telemetry()
        self.root.after(16, self.animate)

    def update_telemetry(self):
        speed_ms = math.hypot(self.ball["vx"], self.ball["vy"], self.ball["vz"])
        text = (f"Speed: {speed_ms*3.6:4.0f} km/h\n"
                f"Pos: X:{self.ball['x']:4.1f} Z:{self.ball['z']:4.1f} Y:{self.ball['y']:4.1f}")
        self.telemetry_label.config(text=text)

    def launch_ball(self):
        self.spawn_ball_in_front_of_player()
        speed = self.speed_var.get()
        elev = math.radians(self.elev_var.get())
        azim = math.radians(self.azim_var.get())

        self.ball["vx"] = speed * math.cos(elev) * math.sin(azim)
        self.ball["vy"] = speed * math.sin(elev)
        self.ball["vz"] = speed * math.cos(elev) * math.cos(azim)

        self.status_var.set("In Play")
        self.running = True

    def toggle_pause(self):
        if self.status_var.get() != "Ready":
            self.running = not self.running

    def toggle_camera_mode(self):
        self.camera_mode = "third_person" if self.camera_mode == "first_person" else "first_person"
        self.status_var.set("Third Person View" if self.camera_mode == "third_person" else "First Person View")

    def reset_ball(self):
        self.running = False
        self.spawn_ball_in_front_of_player()
        self.status_var.set("Ready")
        self.render_scene()

    def handle_canvas_click(self, event):
        if self.ball_is_under_cursor(event.x, event.y):
            self.dragging_ball = True
            self.status_var.set("Dragging ball")
            self.render_scene()

    def handle_canvas_drag(self, event):
        if not self.dragging_ball:
            return
        x, z = self.inverse_project_floor(event.x, event.y)
        if x is None or z is None:
            return
        self.ball["x"] = max(-6.2, min(x, 6.2))
        self.ball["y"] = self.ball_radius
        self.ball["z"] = max(-9.8, min(z, 9.8))
        self.ball["vx"] = self.ball["vy"] = self.ball["vz"] = 0.0
        self.running = False
        self.status_var.set("Ball repositioned")
        self.render_scene()

    def handle_canvas_release(self, event):
        self.dragging_ball = False

    def ball_is_under_cursor(self, screen_x, screen_y):
        px, py, _ = self.project_3d_to_2d(self.ball["x"], self.ball["y"], self.ball["z"])
        r = max(8, int((self.ball_radius * self.focal_length) / max(0.2, self.project_3d_to_2d(self.ball["x"], self.ball["y"], self.ball["z"])[2])))
        return (screen_x - px) ** 2 + (screen_y - py) ** 2 <= r * r


if __name__ == "__main__":
    root = tk.Tk()
    app = FirstPersonVolleyballSim(root)
    root.mainloop()