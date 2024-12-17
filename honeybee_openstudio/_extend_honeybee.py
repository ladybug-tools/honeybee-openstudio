# coding=utf-8
# import all of the modules for writing geometry to OpenStudio
import honeybee.writer.shademesh as shade_mesh_writer
import honeybee.writer.door as door_writer
import honeybee.writer.aperture as aperture_writer
import honeybee.writer.shade as shade_writer
import honeybee.writer.face as face_writer
import honeybee.writer.room as room_writer
import honeybee.writer.model as model_writer

from .writer import model_to_openstudio, room_to_openstudio, face_to_openstudio, \
    aperture_to_openstudio, door_to_openstudio, shade_to_openstudio, \
    shade_mesh_to_openstudio


# add writers to the honeybee-core modules
model_writer.openstudio = model_to_openstudio
room_writer.openstudio = room_to_openstudio
face_writer.openstudio = face_to_openstudio
shade_writer.openstudio = shade_to_openstudio
aperture_writer.openstudio = aperture_to_openstudio
door_writer.openstudio = door_to_openstudio
shade_mesh_writer.openstudio = shade_mesh_to_openstudio
