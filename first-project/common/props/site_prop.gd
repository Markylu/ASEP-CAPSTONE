extends RefCounted
class_name SiteProp

## Constants shared by every prop a site can contain.
##
## The only thing here is the group name. A prop joins it, `run_session.gd`
## connects to every member and forwards what they emit to the recorder, and
## neither side has to know what the other is — a door added today is logged by
## code written for an occluder yesterday.
##
## It lives in its own file so the string has exactly one definition:
## `TriggeredOccluder.EVENT_GROUP` used to be it, which quietly made every
## future prop depend on the occluder.

## Props that report timeline events join this group.
const EVENT_GROUP := "vlmnav_event_source"
