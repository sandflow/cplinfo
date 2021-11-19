#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright (c) Sandflow Consulting LLC
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import xml.etree.ElementTree as et
import argparse
from dataclasses import dataclass
from enum import Enum
import uuid
import re
import logging
import json
import typing
from fractions import Fraction
import hashlib
import time

LOGGER = logging.getLogger(__name__)

def split_qname(qname: str):
  m = re.match(r'\{(.*)\}(.*)', qname)
  return (m.group(1) if m else None, m.group(2) if m else None)

def cpl_rational_to_fraction(r: str) -> Fraction:
  return Fraction(*map(int, r.split()))

def smpte_ul_lookup(u):
  label : str
  if u in ul_list:
    label = ul_list[u]
  else:
    label = None
  return label

REGXML_NS = {
  "r0" : "http://www.smpte-ra.org/reg/395/2014/13/1/aaf",
  "r1" : "http://www.smpte-ra.org/reg/335/2012",
  "r2" : "http://www.smpte-ra.org/reg/2003/2012"
}

LABELS_NS = {"labels" : "http://www.smpte-ra.org/schemas/400/2012"}

COMPATIBLE_CPL_NS = set((
  "http://www.smpte-ra.org/schemas/2067-3/2016",
  "http://www.smpte-ra.org/schemas/2067-3/2013"
))

COMPATIBLE_CORE_NS = set((
  "http://www.smpte-ra.org/schemas/2067-2/2013",
  "http://www.smpte-ra.org/schemas/2067-2/2016",
  "http://www.smpte-ra.org/ns/2067-2/2020"
))


class MainImageVirtualTrack:
  """Image information"""

  sample_rate: Fraction
  stored_width: int
  stored_height: int
  fingerprint: str

  def __init__(self, descriptor_element: et.Element, fingerprint: str, track_id, duration, resources) -> None:
    self.sample_rate = Fraction(descriptor_element.findtext(".//r1:SampleRate", namespaces=REGXML_NS))
    self.stored_width = int(descriptor_element.findtext(".//r1:StoredWidth", namespaces=REGXML_NS))
    self.stored_height = int(descriptor_element.findtext(".//r1:StoredHeight", namespaces=REGXML_NS))
    self.picture_compression = str(descriptor_element.findtext(".//r1:PictureCompression", namespaces=REGXML_NS))
    self.container_format = str(descriptor_element.findtext(".//r1:ContainerFormat", namespaces=REGXML_NS))
    self.transfer_characteristic = str(descriptor_element.findtext(".//r1:TransferCharacteristic", namespaces=REGXML_NS))
    self.coding_equations = str(descriptor_element.findtext(".//r1:CodingEquations", namespaces=REGXML_NS))
    self.color_primaries = str(descriptor_element.findtext(".//r1:ColorPrimaries", namespaces=REGXML_NS))
    self.fingerprint = fingerprint
    self.track_id = track_id
    self.duration = duration
    self.resources = resources

  def to_dict(self) -> dict:
    return {
      "kind": "main_image",
      "fingerprint": self.fingerprint,
      "virtual_track_id": self.track_id,
      "resource_count": self.resources,
      "duration" : str(time.strftime('%H:%M:%S.%s', time.gmtime(round(float(self.duration), 3)))),
      "essence_info": {
        "sample_rate": str(self.sample_rate),
        "stored_width": self.stored_width,
        "stored_height": self.stored_height,
        "picture_compression": smpte_ul_lookup(self.picture_compression),
        "container_format": smpte_ul_lookup(self.container_format),
        "transfer_characteristic": smpte_ul_lookup(self.transfer_characteristic),
        "coding_equations": smpte_ul_lookup(self.coding_equations),
        "color_encoding": smpte_ul_lookup(self.color_primaries)
      }
    }

class MainAudioVirtualTrack:
  """Sound information"""

  @property
  def kind(self) -> str:
    return "main_audio"

  sample_rate: Fraction
  channels: typing.List[str]
  soundfield: str
  fingerprint: str

  def __init__(self, descriptor_element: et.Element, fingerprint: str, track_id, duration, resources) -> None:
    self.sample_rate = Fraction(descriptor_element.findtext(".//r1:SampleRate", namespaces=REGXML_NS))
    self.spoken_language = descriptor_element.findtext(".//r1:RFC5646SpokenLanguage", namespaces=REGXML_NS)
    self.fingerprint = fingerprint
    self.track_id = track_id
    self.duration = duration
    self.resources = resources
    self.channels = [x.text for x in descriptor_element.findall(".//r0:AudioChannelLabelSubDescriptor/r1:MCATagSymbol", namespaces=REGXML_NS)]
    self.soundfield = descriptor_element.findtext(".//r0:SoundfieldGroupLabelSubDescriptor/r1:MCATagSymbol", namespaces=REGXML_NS)
    self.container_format = str(descriptor_element.findtext(".//r1:ContainerFormat", namespaces=REGXML_NS))
    self.channel_assignment = str(descriptor_element.findtext(".//r1:ChannelAssignment", namespaces=REGXML_NS))

  def to_dict(self) -> dict:
    return {
      "kind": "main_audio",
      "fingerprint": self.fingerprint,
      "virtual_track_id": self.track_id,
      "resource_count": self.resources,
      "duration": str(time.strftime('%H:%M:%S.%s', time.gmtime(round(float(self.duration), 3)))),
      "essence_info": {
        "sample_rate": str(self.sample_rate),
        "spoken_language": str(self.spoken_language),
        "soundfield": self.soundfield,
        "container_format": smpte_ul_lookup(self.container_format),
        "channel_assignment": smpte_ul_lookup(self.channel_assignment),
        "channels": self.channels
      }
    }

class SubtitlesSequence:
  """Subtitle information"""

  @property
  def kind(self) -> str:
    return "main_subtitle"

  sample_rate: Fraction
  channels: typing.List[str]
  soundfield: str
  fingerprint: str

  def __init__(self, descriptor_element: et.Element, fingerprint: str, track_id, duration, resources) -> None:
    self.sample_rate = Fraction(descriptor_element.findtext(".//r1:SampleRate", namespaces=REGXML_NS))
    self.subtitle_language = descriptor_element.findtext(".//r2:RFC5646LanguageTagList", namespaces=REGXML_NS)
    self.fingerprint = fingerprint
    self.track_id = track_id
    self.duration = duration
    self.resources = resources
    self.container_format = str(descriptor_element.findtext(".//r1:ContainerFormat", namespaces=REGXML_NS))

  def to_dict(self) -> dict:
    return {
      "kind": "main_subtitle",
      "fingerprint": self.fingerprint,
      "virtual_track_id": self.track_id,
      "resource_count": self.resources,
      "duration": str(time.strftime('%H:%M:%S.%s', time.gmtime(round(float(self.duration), 3)))),
      "essence_info": {
        "sample_rate": str(self.sample_rate),
        "subtitle_language": str(self.subtitle_language),
        "container_format": smpte_ul_lookup(self.container_format)
      }
    }

class CPLInfo:
  """CPL information"""
  namespace: str
  content_title: str
  edit_rate: Fraction
  virtual_tracks: typing.List[typing.Any]

  def __init__(self, cpl_element: et.Element) -> None:
    self.namespace, local_name = split_qname(cpl_element.tag)

    if self.namespace not in COMPATIBLE_CPL_NS:
      LOGGER.error("Unknown CompositionPlaylist namespace: %s", self.namespace)

    if local_name != "CompositionPlaylist":
      LOGGER.error("Unknown CompositionPlaylist element name: %s", local_name)

    ns_dict = {"cpl": self.namespace}

    self.content_title = cpl_element.findtext(".//cpl:ContentTitle", namespaces=ns_dict)

    self.edit_rate = cpl_rational_to_fraction(cpl_element.findtext(".//cpl:EditRate", namespaces=ns_dict))

    self.virtual_tracks = []

    sequence_list = cpl_element.find("./cpl:SegmentList/cpl:Segment/cpl:SequenceList", namespaces=ns_dict)

    for sequence in sequence_list:
      track_id = sequence.findtext("cpl:TrackId", namespaces=ns_dict)

      if track_id is None:
        LOGGER.error("Sequence is missing TrackId")
        continue

      sequence_ns, sequence_name = split_qname(sequence.tag)

      if sequence_ns not in COMPATIBLE_CORE_NS:
        LOGGER.warning("Unknown virtual track namespace %s", sequence_ns)
        continue

      if sequence_name == "MainImageSequence":
        vt_class = MainImageVirtualTrack
      elif sequence_name == "MainAudioSequence":
        vt_class = MainAudioVirtualTrack
      elif sequence_name == "SubtitlesSequence":
        vt_class = SubtitlesSequence
      else:
        LOGGER.warning("Unknown Sequence kind: %s", sequence_name)
        continue

      source_encoding = sequence.findtext(".//cpl:SourceEncoding", namespaces=ns_dict)

      if source_encoding is None:
        LOGGER.error("Cannot find source encoding descriptor")
        continue

      essence_descriptor = cpl_element.find(f".//cpl:EssenceDescriptor[cpl:Id='{source_encoding}']", namespaces=ns_dict)

      if essence_descriptor is None:
        LOGGER.error("Cannot find essence descriptor")
        continue

      resources = cpl_element.findall(f"./cpl:SegmentList/cpl:Segment/cpl:SequenceList/*[cpl:TrackId='{track_id}']/cpl:ResourceList/cpl:Resource", namespaces=ns_dict)

      fingerprint = hashlib.sha1()

      total_duration = 0

      for resource in resources:
        edit_rate = cpl_rational_to_fraction(resource.findtext(".//cpl:EditRate", namespaces=ns_dict)) or self.edit_rate

        entry_point = edit_rate * int(resource.findtext(".//cpl:EntryPoint", namespaces=ns_dict) or 0)

        duration = int(resource.findtext(".//cpl:SourceDuration", namespaces=ns_dict) or resource.findtext(".//cpl:IntrinsicDuration", namespaces=ns_dict)) / float(edit_rate)

        if duration == 0:
          continue
        total_duration += duration

        repeat_count = int(resource.findtext(".//cpl:RepeatCount", namespaces=ns_dict) or 1)

        trackfile_id = resource.findtext(".//cpl:TrackFileId", namespaces=ns_dict)

        fingerprint.update(bytes(str(entry_point), 'ascii'))
        fingerprint.update(bytes(str(duration), 'ascii'))
        fingerprint.update(bytes(str(repeat_count), 'ascii'))
        fingerprint.update(bytes(str(trackfile_id), 'ascii'))

      self.virtual_tracks.append(vt_class(essence_descriptor, fingerprint.hexdigest(), track_id, total_duration, len(resources)))

  def to_dict(self) -> dict:
    return {
      "namespace": self.namespace,
      "content_title": self.content_title,
      "virtual_tracks" : [vt.to_dict() for vt in self.virtual_tracks]
    }

def main():
  parser = argparse.ArgumentParser(description="Extracts Composition information from an IMF CPL document")
  parser.add_argument('cpl_file', type=argparse.FileType(mode='r',encoding="UTF-8"), help='Path to the CPL document')
  args = parser.parse_args()

  cpl_doc = et.parse(args.cpl_file)

  smpte_ul_doc = et.parse("smpte_ul_labels.xml")
  
  smpte_ul_labels = smpte_ul_doc.getroot()
  global ul_list
  ul_list = {}
  for entry in smpte_ul_labels.findall('.//labels:Entry', LABELS_NS):
    name = entry.find('labels:Name', LABELS_NS)
    ul = entry.find('labels:UL', LABELS_NS)
    ul_list[ul.text] = name.text

  cpl_info = CPLInfo(cpl_doc.getroot())

  print(json.dumps(cpl_info.to_dict(), indent="  "))

if __name__ == "__main__":
  main()
