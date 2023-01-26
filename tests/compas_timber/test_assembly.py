from copy import deepcopy

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector

# import pytest
from compas_timber.assembly.assembly import TimberAssembly
from compas_timber.connections.joint import Joint
from compas_timber.parts.beam import Beam


def test_create():
    _ = TimberAssembly()


def test_add_beam():
    A = TimberAssembly()
    B = Beam(Frame.worldXY(), width=0.1, height=0.1, length=1.0)
    A.add_beam(B)

    assert B.key in A.beam_keys
    assert B in A.beams
    assert B.assembly is A
    assert len(list(A.graph.nodes())) == 1
    assert len(list(A.graph.edges())) == 0
    assert A.beams[0] == B
    assert len(A.beams) == 1


def test_add_joint():
    A = TimberAssembly()
    B1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    B2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)

    A.add_beam(B1)
    A.add_beam(B2)
    _ = Joint.create(A, [B1, B2])

    assert len(list(A.graph.nodes())) == 3
    assert len(list(A.graph.edges())) == 2
    assert A.beams[0] == B1
    assert len(A.joints) == 1


def test_remove_joint():
    A = TimberAssembly()
    B1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    B2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    A.add_beam(B1)
    A.add_beam(B2)

    J = Joint.create(A, [B1, B2])
    assert A.contains(J)

    A.remove_joint(J)
    assert len(list(A.graph.nodes())) == 2
    assert len(list(A.graph.edges())) == 0
    assert len(A.joints) == 0
    assert J.assembly is None


def test_copy(mocker):
    mocker.patch("compas_timber.parts.Beam.update_beam_geometry")
    mocker.patch("compas_timber.connections.Joint.add_features")
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    B1 = Beam(F1, length=1.0, width=0.1, height=0.12, geometry_type="brep")
    B2 = Beam(F2, length=1.0, width=0.1, height=0.12, geometry_type="brep")
    A = TimberAssembly()
    A.add_beam(B1)
    A.add_beam(B2)
    _ = Joint.create(A, [B1, B2])

    A_copy = A.copy()
    assert A_copy is not A
    assert A_copy.beams[0].is_identical(A.beams[0])
    assert A_copy.beams[0] is not A.beams[0]
    assert A_copy.beams[0].assembly is not A
    # different parts in the assembly should point back to the same assembly
    assert A_copy.beams[0].assembly is A_copy.beams[1].assembly


def test_deepcopy(mocker):
    mocker.patch("compas_timber.parts.Beam.update_beam_geometry")
    mocker.patch("compas_timber.connections.Joint.add_features")
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    B1 = Beam(F1, length=1.0, width=0.1, height=0.12)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.12)
    A = TimberAssembly()
    A.add_beam(B1)
    A.add_beam(B2)
    _ = Joint.create(A, [B1, B2])

    A_copy = deepcopy(A)
    assert A_copy is not A
    assert A_copy.beams[0].is_identical(A.beams[0])
    assert A_copy.beams[0] is not A.beams[0]
    assert A_copy.beams[0].assembly is not A
    assert (
        A_copy.beams[0].assembly is A_copy.beams[1].assembly
    )  # different parts in the assembly should point back to the same assembly


def test_find():
    A = TimberAssembly()
    B = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    A.add_beam(B)
    assert B == A.find(B.guid)


def test_parts_joined():
    A = TimberAssembly()
    B1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    B2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    B3 = Beam(Frame.worldZX(), length=1.0, width=0.1, height=0.1)

    A.add_beam(B1)
    A.add_beam(B2)
    A.add_beam(B3)
    _ = Joint.create(A, [B1, B2])
    assert A.are_parts_joined([B1, B2])
    assert not A.are_parts_joined([B1, B3])


if __name__ == "__main__":
    # TODO: run with `invoke test` instead
    test_create()
    test_add_beam()
    test_add_joint()
    test_remove_joint()
    # test_copy()
    # test_deepcopy()
    test_find()
    test_parts_joined()
    print("\n *** all tests passed ***\n\n")
