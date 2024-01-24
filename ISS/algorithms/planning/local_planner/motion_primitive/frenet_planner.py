"""

Frenet optimal trajectory generator in carla

author: lqz27 lirj19

Ref:

- PythonRobotics: Atsushi Sakai (@Atsushi_twi)

- RL-frenet-trajectory-planning-in-CARLA: Majid Moghadam

- [Optimal Trajectory Generation for Dynamic Street Scenarios in a Frenet Frame]
(https://www.researchgate.net/profile/Moritz_Werling/publication/224156269_Optimal_Trajectory_Generation_for_Dynamic_Street_Scenarios_in_a_Frenet_Frame/links/54f749df0cf210398e9277af.pdf)

- [Optimal trajectory generation for dynamic street scenarios in a Frenet Frame]
(https://www.youtube.com/watch?v=Cj6tAQe7UCY)

"""

import numpy as np
import math
from scipy.spatial import KDTree

from ISS.algorithms.utils.trajectory import Trajectory
from ISS.algorithms.utils.cubic_spline import Spline2D
from ISS.algorithms.utils.quartic_polynomial import QuarticPolynomial
from ISS.algorithms.utils.quintic_polynomial import QuinticPolynomial
from ISS.algorithms.utils.angle import pi_2_pi

class FrenetPath:

    def __init__(self):
        self.t = []
        self.d = []
        self.d_d = []
        self.d_dd = []
        self.d_ddd = []
        self.s = []
        self.s_d = []
        self.s_dd = []
        self.s_ddd = []
        self.cd = 0.0
        self.cv = 0.0
        self.cf = 0.0
        
        self.x = []
        self.y = []
        self.yaw = []
        self.v = []
        self.ds = []
        self.c = []
        self.T = 0 # duration
        
        self.zero = False


class FrenetPlanner(object):

    def __init__(self, settings) -> None:
        # Parameters
        for keys in settings:
            self.__dict__[keys] = settings[keys]

        # Initialize
        self.waypoints_xy = None
        self.state_frenet = None
        self.state_cartesian = None
        self.state_cartesian_prev = None
        self.best_path = None

    def update_reference_line(self, waypoints):
        self.waypoints_xy = waypoints
        self.rx, self.ry, self.ryaw, self.rk, self.csp = self._generate_target_course()
        point_xy = np.array([item for item in zip(self.rx, self.ry)])
        self.ref_kdtree = KDTree(point_xy)

    def _generate_target_course(self):
        x = [waypoint[0] for waypoint in self.waypoints_xy]
        y = [waypoint[1] for waypoint in self.waypoints_xy]
        self.csp = Spline2D(x, y)
        self.s = np.arange(0, self.csp.s[-1], 0.1)
        self.rx, self.ry, self.ryaw, self.rk = [], [], [], []
        for i_s in self.s:
            ix, iy = self.csp.calc_position(i_s)
            self.rx.append(ix)
            self.ry.append(iy)
            self.ryaw.append(self.csp.calc_yaw(i_s))
            self.rk.append(self.csp.calc_curvature(i_s))
        return self.rx, self.ry, self.ryaw, self.rk, self.csp

    def _calc_frenet_paths(self):
        frenet_paths = []
        if self.state_frenet is None:
            return frenet_paths
        s, s_d, s_dd, d, d_d, d_dd = self.state_frenet
        d_r, d_l = self.d_r, -self.d_l
        for Ti in np.arange(self.MIN_T, self.MAX_T + self.D_T, self.D_T):
            for tv in np.arange(self.MIN_SPEED, self.MAX_SPEED + self.D_V_S, self.D_V_S):
                lon_qp = QuarticPolynomial(s, s_d, 0, tv, 0.0, Ti)
                for di in np.arange(d_l, d_r + self.D_S, self.D_S):
                    lat_qp = QuinticPolynomial(d, d_d, d_dd, di, 0.0, 0.0, Ti)
                    fp = FrenetPath()
                    fp.T = Ti
                    fp.t = list(np.arange(0.0, Ti, self.dt))
                    fp.d = [lat_qp.calc_point(t) for t in fp.t]
                    fp.d_d = [lat_qp.calc_first_derivative(t) for t in fp.t]
                    fp.d_dd = [lat_qp.calc_second_derivative(t) for t in fp.t]
                    fp.d_ddd = [lat_qp.calc_third_derivative(t) for t in fp.t]
                    fp.s = [lon_qp.calc_point(t) for t in fp.t]
                    fp.s_d = [lon_qp.calc_first_derivative(t) for t in fp.t]
                    fp.s_dd = [lon_qp.calc_second_derivative(t) for t in fp.t]
                    fp.s_ddd = [lon_qp.calc_third_derivative(t) for t in fp.t]
                    
                    Jp = sum(np.power(fp.d_ddd, 2))  # square of jerk
                    Js = sum(np.power(fp.s_ddd, 2))  # square of jerk
                    ds = (self.TARGET_SPEED - fp.s_d[-1]) ** 2  # square of diff from target speed

                    # cost
                    fp.cd = self.K_J * Jp + self.K_T * Ti + self.K_D * fp.d[-1] ** 2
                    fp.cv = self.K_J * Js + self.K_T * Ti + self.K_D * ds
                    fp.cf = self.K_LAT * fp.cd + self.K_LON * fp.cv
                    
                    if tv == 0 and di == 0:
                        fp.zero = True
                    frenet_paths.append(fp)

        return frenet_paths

    def _get_frenet_state(self):
        state_c = self.state_cartesian

        # idx_r = get_closest_waypoints(state_c[0], state_c[1], list(zip(self.rx, self.ry)))
        _, idx_r = self.ref_kdtree.query([state_c[0], state_c[1]])

        s_r = self.s[idx_r]
        x_r, y_r = self.csp.calc_position(s_r)
        x1_r, y1_r = self.rx[idx_r], self.ry[idx_r]

        k_r = self.csp.calc_curvature(s_r)
        yaw_r = self.csp.calc_yaw(s_r)
        dyaw_r = self.csp.calc_curvature_d(s_r)
        delta_theta = state_c[2] - yaw_r

        # k_x: curvature of vehicle's route
        if self.state_cartesian is not None and self.state_cartesian_prev is not None:
            dx = self.state_cartesian[0] - self.state_cartesian_prev[0]
            dy = self.state_cartesian[1] - self.state_cartesian_prev[1]
            dyaw = self.state_cartesian[2] - self.state_cartesian_prev[2]
            ds = math.hypot(dx, dy)
            if 0 < ds:
                k_x = dyaw / math.hypot(dx, dy)
            else:
                k_x = None
        else:
            k_x = None

        # s, d = get_frenet_coord(state_c[0], state_c[1], list(zip(self.rx, self.ry)))
        s = s_r
        x_delta = self.state_cartesian[0] - x_r
        y_delta = self.state_cartesian[1] - y_r
        d = np.sign(y_delta * math.cos(yaw_r) - x_delta *
                    math.sin(yaw_r)) * math.hypot(x_delta, y_delta)
        d_d = state_c[3] * math.sin(delta_theta)

        coeff_1 = 1 - k_r * d

        d_dd = state_c[4] * math.sin(delta_theta)
        s_d = state_c[3] * math.cos(delta_theta) / coeff_1

        if k_x is None:
            s_dd = 0
        else:
            s_ds = coeff_1 * math.tan(delta_theta)
            coeff_2 = coeff_1 / math.cos(delta_theta) * k_x - k_r
            coeff_3 = dyaw_r * d + yaw_r * s_ds
            s_dd = state_c[4] * math.cos(delta_theta) - \
                (s_d ** 2) * (s_ds * coeff_2 - coeff_3) / coeff_1

        self.state_frenet = [s, s_d, s_dd, d, d_d, d_dd]

        return self.state_frenet

    def _calc_curvature_paths(self, fp):
        # find curvature
        # source: http://www.kurims.kyoto-u.ac.jp/~kyodo/kokyuroku/contents/pdf/1111-16.pdf
        # and https://math.stackexchange.com/questions/2507540/numerical-way-to-solve-for-the-curvature-of-a-curve

        n_t = len(fp.t)
        n_x = len(fp.x)
        n = min(n_x, n_t)

        fp.c.append(0.0)
        for i in range(1, n - 1):
            a = np.hypot(fp.x[i - 1] - fp.x[i], fp.y[i - 1] - fp.y[i])
            b = np.hypot(fp.x[i] - fp.x[i + 1], fp.y[i] - fp.y[i + 1])
            c = np.hypot(fp.x[i + 1] - fp.x[i - 1], fp.y[i + 1] - fp.y[i - 1])

            # Compute inverse radius of circle using surface of triangle (for which Heron's formula is used)
            k = np.sqrt(np.abs((a + (b + c)) * (c - (a - b)) * (c + (a - b)) * (
                a + (b - c)))) / 4  # Heron's formula for triangle's surface
            # Denumerator; make sure there is no division by zero.
            den = a * b * c
            if den == 0.0:  # just for sure
                fp.c.append(0.0)
            else:
                fp.c.append(4 * k / den)
        fp.c.append(0.0)

        return fp

    def _calc_global_paths(self, fplist):
        transformed_fplist = []
        for fp in fplist:
            is_valid = True
            x, y, v, yaw, ds = [], [], [], [], []

            # Transform Frenet to Cartesian coordinates
            for s, d, s_d, d_d in zip(fp.s, fp.d, fp.s_d, fp.d_d):
                ix, iy = self.csp.calc_position(s)
                if ix is None or iy is None:
                    is_valid = False
                    break
                i_yaw = self.csp.calc_yaw(s)
                fx = ix + d * math.cos(i_yaw + math.pi / 2.0)
                fy = iy + d * math.sin(i_yaw + math.pi / 2.0)
                fv = math.hypot(s_d, d_d)
                x.append(fx)
                y.append(fy)
                v.append(fv)
            
            if not is_valid:
                continue
            
            # Calculate yaw and ds
            for i in range(len(x) - 1):
                dx = x[i + 1] - x[i]
                dy = y[i + 1] - y[i]
                yaw.append(math.atan2(dy, dx))
                ds.append(math.hypot(dx, dy))

            # Append last yaw and ds for consistency
            yaw.append(yaw[-1])
            ds.append(ds[-1])

            # Update the fp object or create a new structure for the transformed path
            fp.x, fp.y, fp.v, fp.yaw, fp.ds = x, y, v, yaw, ds
            # Assuming _calc_curvature_paths is another method to process the path
            transformed_fplist.append(self._calc_curvature_paths(fp))

        return transformed_fplist

    def _check_paths(self, fplist, motion_predictor):
        print("-------------------")
        ok_ind = []
        speed = 0
        accel = 0
        curvature = 0
        obstacle = 0
        solid_boundary = 0
        all_path_vis = []
        frenet_path_duration = -1
        for i, frenet_path in enumerate(fplist):
            path_vis = [[x, y, yaw] for x, y, yaw in zip(
                    frenet_path.x, frenet_path.y, frenet_path.yaw)]
            all_path_vis.append([path_vis, "safe"])
            if any([self.MAX_SPEED < v for v in frenet_path.s_d]):
                speed += 1
                all_path_vis[-1][-1] = "velocity"
                continue
            elif any([self.MAX_ACCEL < a for a in frenet_path.s_dd]) and (frenet_path.s_dd[0] < self.MAX_ACCEL):
                accel += 1
                all_path_vis[-1][-1] = "acceleration"
                continue
            # elif any([self.MAX_CURVATURE < abs(c) for c in frenet_path.c]):
            #     curvature += 1
            #     all_path_vis[-1][-1] = "curvature"
            #     if frenet_path.zero:
            #         print("error in curvature")
            #         print(max(frenet_path.c))
            #     continue
            else:
                frenet_path_tuple = [(x, y, yaw) for x, y, yaw in zip(
                    frenet_path.x, frenet_path.y, frenet_path.yaw)]
                
                if frenet_path.T != frenet_path_duration:
                    motion_predictor.update_prediction(frenet_path.t[1], len(frenet_path.t))
                    frenet_path_duration = frenet_path.T
                
                res, coll_type = motion_predictor.collision_check(frenet_path_tuple)
                if res:
                    if frenet_path.zero:
                        print("error in obstacle with collision type: ", coll_type)
                        print(frenet_path.v)
                        print(frenet_path_tuple)
                        motion_predictor.save_obstacle()
                    if coll_type == 0:
                        solid_boundary += 1
                        all_path_vis[-1][-1] = "solid_boundary"
                    elif coll_type == 1:
                        obstacle += 1
                        all_path_vis[-1][-1] = "obstacle"
                    continue
            ok_ind.append(i)
        print("before path num: ", len(fplist))
        print("speed: ", speed, "accel: ", accel, "curvature: ", curvature, "obstacle: ", obstacle, "solid_boundary: ", solid_boundary)
        return [fplist[i] for i in ok_ind], all_path_vis
    
    def _path_planning(self, motion_predictor):
        fplist = self._calc_frenet_paths()
        fplist = self._calc_global_paths(fplist)
        fplist, all_path_vis = self._check_paths(fplist, motion_predictor)
        best_path = min(fplist, key=lambda fp: fp.cf, default=None)
        return best_path, all_path_vis
    
    def run_step(self, ego_state, motion_predictor):
        self.state_cartesian_prev = self.state_cartesian
        self.state_cartesian = (ego_state.x, ego_state.y, ego_state.heading_angle, ego_state.velocity, ego_state.acceleration)
        # get curr ego_vehicle's frenet coordinate
        self._get_frenet_state()
        self.best_path, all_path_vis = self._path_planning(motion_predictor)
        states_list = []
        if self.best_path is not None:
            for x, y, yaw, speed, t in zip(self.best_path.x, 
                                           self.best_path.y, 
                                           self.best_path.yaw, 
                                           self.best_path.v, 
                                           self.best_path.t):
                states_list.append([x, y, yaw, speed, 0, 0, 0, 0, t])
        trajectory = Trajectory()
        trajectory.update_states_from_list(states_list)
        return trajectory, all_path_vis
