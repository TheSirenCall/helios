import OpenGL.GL as gl
import OpenGL.GLU as glu
from pxr import UsdGeom
import numpy as np
from PySide6 import QtCore
from PySide6.QtOpenGLWidgets import QOpenGLWidget


class USDViewer(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.usd_file = None
        self.vertices = np.array([], dtype=np.float32)
        self.normals = np.array([], dtype=np.float32)
        self.indices = np.array([], dtype=np.uint32)
        self.camera_pos = [0, 0, 10]
        self.angle_x = 0
        self.angle_y = 0
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.last_mouse_pos = None
        self.bounding_box = None
        self.light_pos = [5.0, 5.0, 5.0, 1.0]  # Positional light
        self.light_move = False

    def initializeGL(self):
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glShadeModel(gl.GL_SMOOTH)
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(45, self.width() / self.height(), 0.1, 100000)
        gl.glMatrixMode(gl.GL_MODELVIEW)

        gl.glEnable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_LIGHT0)

        light_position = [1.0, 1.0, 1.0, 0.0]
        light_color = [1.0, 1.0, 1.0, 1.0]
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, light_position)
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, light_color)
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_SPECULAR, light_color)

        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)

    def resizeGL(self, w, h):
        gl.glViewport(0, 0, w, h)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(45, w / h, 0.1, 100000)
        gl.glMatrixMode(gl.GL_MODELVIEW)

    def paintGL(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glLoadIdentity()
        glu.gluLookAt(self.camera_pos[0] + self.pan_x, self.camera_pos[1] + self.pan_y, self.camera_pos[2] / self.zoom,
                      0, 0, 0, 0, 1, 0)
        gl.glRotatef(self.angle_x, 1, 0, 0)
        gl.glRotatef(self.angle_y, 0, 1, 0)

        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, self.light_pos)

        # Draw grid
        gl.glColor3f(0.5, 0.5, 0.5)
        gl.glBegin(gl.GL_LINES)
        for i in range(-10, 11):
            gl.glVertex3f(i, 0, -10)
            gl.glVertex3f(i, 0, 10)
            gl.glVertex3f(-10, 0, i)
            gl.glVertex3f(10, 0, i)
        gl.glEnd()

        if self.vertices.size > 0:
            # Set material properties
            material_diffuse = [0.7, 0.7, 0.7, 1.0]
            material_specular = [1.0, 1.0, 1.0, 1.0]
            material_shininess = [50.0]
            gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_DIFFUSE, material_diffuse)
            gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_SPECULAR, material_specular)
            gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_SHININESS, material_shininess)

            # Draw geometry
            gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
            gl.glEnableClientState(gl.GL_NORMAL_ARRAY)
            gl.glVertexPointer(3, gl.GL_FLOAT, 0, self.vertices)
            gl.glNormalPointer(gl.GL_FLOAT, 0, self.normals)
            gl.glDrawElements(gl.GL_TRIANGLES, len(self.indices), gl.GL_UNSIGNED_INT, self.indices)
            gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
            gl.glDisableClientState(gl.GL_NORMAL_ARRAY)

            # Draw bounding box
            if self.bounding_box:
                gl.glColor3f(1.0, 0.0, 0.0)
                gl.glBegin(gl.GL_LINE_LOOP)
                for i in range(8):
                    gl.glVertex3fv(self.bounding_box[i])
                gl.glEnd()

    def extract_geometry(self, usd_stage):
        vertices = []
        normals = []
        indices = []
        bbox_min = [float('inf')] * 3
        bbox_max = [float('-inf')] * 3

        for prim in usd_stage.Traverse():
            if prim.IsA(UsdGeom.Mesh):
                mesh = UsdGeom.Mesh(prim)
                points = mesh.GetPointsAttr().Get()
                face_vertex_counts = mesh.GetFaceVertexCountsAttr().Get()
                face_vertex_indices = mesh.GetFaceVertexIndicesAttr().Get()
                normals_attr = mesh.GetNormalsAttr()

                if points and face_vertex_counts and face_vertex_indices:
                    start_idx = len(vertices)
                    vertices.extend([(p[0], p[1], p[2]) for p in points])

                    normals.extend([np.zeros(3) for _ in range(len(points))])

                    idx = 0
                    for count in face_vertex_counts:
                        if count >= 3:
                            face_indices = face_vertex_indices[idx:idx + count]
                            face_vertices = [vertices[start_idx + i] for i in face_indices]

                            v0 = np.array(face_vertices[0])
                            v1 = np.array(face_vertices[1])
                            v2 = np.array(face_vertices[2])
                            face_normal = np.cross(v1 - v0, v2 - v0)
                            norm = np.linalg.norm(face_normal)

                            if norm > 1e-6:
                                face_normal /= norm
                            else:
                                idx += count
                                continue

                            for i in face_indices:
                                normals[start_idx + i] += face_normal

                        idx += count

                    for i in range(len(normals)):
                        norm = np.linalg.norm(normals[i])
                        if norm > 1e-6:
                            normals[i] /= norm
                        else:
                            normals[i] = np.array([0.0, 1.0, 0.0])

                    idx = 0
                    for count in face_vertex_counts:
                        if count == 3:
                            indices.extend([face_vertex_indices[idx + i] + start_idx for i in range(3)])
                        elif count == 4:
                            indices.extend([
                                face_vertex_indices[idx] + start_idx,
                                face_vertex_indices[idx + 1] + start_idx,
                                face_vertex_indices[idx + 2] + start_idx,
                                face_vertex_indices[idx] + start_idx,
                                face_vertex_indices[idx + 2] + start_idx,
                                face_vertex_indices[idx + 3] + start_idx,
                            ])
                        else:
                            for i in range(1, count - 1):
                                indices.extend([
                                    face_vertex_indices[idx] + start_idx,
                                    face_vertex_indices[idx + i] + start_idx,
                                    face_vertex_indices[idx + i + 1] + start_idx,
                                ])
                        idx += count

                    for p in points:
                        for i in range(3):
                            bbox_min[i] = min(bbox_min[i], p[i])
                            bbox_max[i] = max(bbox_max[i], p[i])

        center = [(bbox_min[i] + bbox_max[i]) / 2 for i in range(3)]
        scale = 2.0 / max(bbox_max[i] - bbox_min[i] for i in range(3))
        vertices = [((v[0] - center[0]) * scale,
                     (v[1] - center[1]) * scale,
                     (v[2] - center[2]) * scale) for v in vertices]

        self.bounding_box = [
            [bbox_min[0], bbox_min[1], bbox_min[2]],
            [bbox_max[0], bbox_min[1], bbox_min[2]],
            [bbox_max[0], bbox_max[1], bbox_min[2]],
            [bbox_min[0], bbox_max[1], bbox_min[2]],
            [bbox_min[0], bbox_min[1], bbox_max[2]],
            [bbox_max[0], bbox_min[1], bbox_max[2]],
            [bbox_max[0], bbox_max[1], bbox_max[2]],
            [bbox_min[0], bbox_max[1], bbox_max[2]]
        ]
        return np.array(vertices, dtype=np.float32), np.array(normals, dtype=np.float32), np.array(indices,
                                                                                                   dtype=np.uint32)

    def mousePressEvent(self, event):
        self.last_mouse_pos = event.position()
        self.light_move = (event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier)

    def mouseMoveEvent(self, event):
        if self.last_mouse_pos:
            dx = event.position().x() - self.last_mouse_pos.x()
            dy = event.position().y() - self.last_mouse_pos.y()

            if self.light_move:
                # Move light with mouse
                self.light_pos[0] += dx * 0.1
                self.light_pos[1] -= dy * 0.1
            elif event.modifiers() == QtCore.Qt.KeyboardModifier.AltModifier:
                # Original camera controls
                if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
                    self.angle_x += dy * 0.5
                    self.angle_y += dx * 0.5
                elif event.buttons() == QtCore.Qt.MouseButton.MiddleButton:
                    self.pan_x += dx * 0.01
                    self.pan_y -= dy * 0.01
                elif event.buttons() == QtCore.Qt.MouseButton.RightButton:
                    self.zoom *= 1.0 + (dy * 0.01)
            self.update()
        self.last_mouse_pos = event.position()
    def wheelEvent(self, event):
        self.zoom *= 1.0 + (event.angleDelta().y() * 0.001)
        self.update()