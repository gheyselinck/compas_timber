from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane
from compas.geometry import length_vector
from compas.geometry import midpoint_point_point


from compas_timber.utils import intersection_line_line_3D
from .joint import beam_side_incidence
from compas_timber.parts import CutFeature
from compas_timber.parts import MillVolume
from .joint import Joint
from .solver import JointTopology


class THalfLapJoint(Joint):
    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(self, main_beam=None, cross_beam=None, flip_lap_side=False, cut_plane_bias = 0.5, frame=None, key=None):
        super(THalfLapJoint, self).__init__(frame, key)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_key = main_beam.key if main_beam else None
        self.cross_beam_key = cross_beam.key if cross_beam else None
        self.flip_lap_side = flip_lap_side  # Decide if Direction of main_beam or cross_beam
        self.features = []
        self.cut_plane_bias = cut_plane_bias

    @property
    def data(self):
        data_dict = {
            "main_beam": self.main_beam_key,
            "cross_beam": self.cross_beam_key,
        }
        data_dict.update(Joint.data.fget(self))
        return data_dict

    @classmethod
    def from_data(cls, value):
        instance = cls(frame=Frame.from_data(value["frame"]), key=value["key"], cutoff=value["cut_plane_choice"])
        instance.main_beam_key = value["main_beam"]
        instance.cross_beam_key = value["cross_beam"]
        instance.cut_plane_choice = value["cut_plane_choice"]
        return instance

    @property
    def joint_type(self):
        return "T-HalfLap"

    @property
    def beams(self):
        return [self.main_beam, self.cross_beam]

    def _cutplane(self):
        # Find the Point for the Cut Plane
        int_a, int_b = intersection_line_line_3D(self.main_beam.centerline, self.cross_beam.centerline, float("inf"))
        int_a, _ = int_a
        int_b, _ = int_b
        point_cut = midpoint_point_point(int_a, int_b)

        # Vector Cross Product
        cross_vector = self.main_beam.centerline.vector.cross(self.cross_beam.centerline.vector)
        return  cross_vector

    @staticmethod
    def _sort_beam_planes(beam, cutplane_vector):
        # Sorts the Beam Face Planes according to the Cut Plane
        frames = beam.faces[:4]
        planes = [Plane.from_frame(frame) for frame in frames]
        planes.sort(key = lambda x: angle_vectors(cutplane_vector, x.normal))
        return planes

    @staticmethod
    def _create_polyhedron(plane_a, lines, bias):  # Hexahedron from 2 Planes and 4 Lines
        # Step 1: Get 8 Intersection Points from 2 Planes and 4 Lines
        int_points = []
        for i in lines:
            point_top = intersection_line_plane(i, plane_a)
            point_bottom = i.point_at(bias)  # intersection_line_plane(i, plane_b
            point_top = Point(*point_top)
            point_bottom = Point(*point_bottom)
            int_points.append(point_top)
            int_points.append(point_bottom)

        # Step 2: Check if int_points Order results in an inward facing Polyhedron
        test_face_vector1 = Vector.from_start_end(int_points[0], int_points[2])
        test_face_vector2 = Vector.from_start_end(int_points[0], int_points[6])
        test_face_normal = Vector.cross(test_face_vector1, test_face_vector2)
        check_vector = Vector.from_start_end(int_points[0], int_points[1])
        # Flip int_points Order if needed
        if angle_vectors(test_face_normal, check_vector) < 1:
            a, b, c, d, e, f, g, h = int_points
            int_points = b, a, d, c, f, e, h, g

        # Step 3: Create a Hexahedron with 6 Faces from the 8 Points
        return Polyhedron(
            int_points,
            [
                [1, 7, 5, 3],  # top
                [0, 2, 4, 6],  # bottom
                [1, 3, 2, 0],  # left
                [3, 5, 4, 2],  # back
                [5, 7, 6, 4],  # right
                [7, 1, 0, 6],  # front
            ],
        )


    @property
    def cutting_plane_main(self):
        angles_faces = beam_side_incidence(self.main_beam, self.cross_beam)
        cfr = max(angles_faces, key=lambda x: x[0])[1]
        cfr = Frame(cfr.point, cfr.yaxis, cfr.xaxis)  # flip normal towards the inside of main beam
        return cfr

    def _create_negative_volumes(self):
        # Get Cut Plane
        plane_cut_vector = self._cutplane()

        if self.flip_lap_side:
            plane_cut_vector = - plane_cut_vector

        # Get Beam Faces (Planes) in right order
        planes_main = self._sort_beam_planes(self.main_beam, plane_cut_vector)
        plane_a0, plane_a1, plane_a2, plane_a3 = planes_main


        planes_cross = self._sort_beam_planes(self.cross_beam, -plane_cut_vector)
        plane_b0, plane_b1, plane_b2, plane_b3 = planes_cross



        # Lines as Frame Intersections
        lines = []
        unbound_line = intersection_plane_plane(plane_a1, plane_b1, tol=1e-6)

        pt_a = (intersection_line_plane(unbound_line, plane_a0))
        pt_b = (intersection_line_plane(unbound_line, plane_b0))
        lines.append(Line(pt_a, pt_b))

        unbound_line = intersection_plane_plane(plane_a1, plane_b2)
        pt_a = intersection_line_plane(unbound_line, plane_a0)
        pt_b = intersection_line_plane(unbound_line, plane_b0)
        lines.append(Line(pt_a, pt_b))

        unbound_line = intersection_plane_plane(plane_a2, plane_b2)
        pt_a = intersection_line_plane(unbound_line, plane_a0)
        pt_b = intersection_line_plane(unbound_line, plane_b0)
        lines.append(Line(pt_a, pt_b))

        unbound_line = intersection_plane_plane(plane_a2, plane_b1)
        pt_a = intersection_line_plane(unbound_line, plane_a0)
        pt_b = intersection_line_plane(unbound_line, plane_b0)
        lines.append(Line(pt_a, pt_b))

        # Create Polyhedrons
        negative_polyhedron_main_beam = self._create_polyhedron(plane_a0, lines, self.cut_plane_bias)
        negative_polyhedron_cross_beam = self._create_polyhedron(plane_b0, lines, self.cut_plane_bias)
        return negative_polyhedron_main_beam, negative_polyhedron_cross_beam

    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.main_beam = assemly.find_by_key(self.main_beam_key)
        self.cross_beam = assemly.find_by_key(self.cross_beam_key)

    def add_features(self):
        start_main, end_main = self.main_beam.extension_to_plane(self.cutting_plane_main)
        print(start_main, end_main)
        self.main_beam.add_blank_extension(start_main, end_main, self.key)

        negative_brep_main_beam, negative_brep_cross_beam = self._create_negative_volumes()
        self.main_beam.add_features(MillVolume(negative_brep_main_beam))
        self.cross_beam.add_features(MillVolume(negative_brep_cross_beam))

        trim_plane = Plane(self.cutting_plane_main.point, -self.cutting_plane_main.normal)
        f_main = CutFeature(trim_plane)
        self.main_beam.add_features(f_main)
        self.features.append(f_main)


