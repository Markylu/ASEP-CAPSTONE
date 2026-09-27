# `common/three_doors/` — the scenes both s02 arms are built from

Not a site, and deliberately not under `sites/`: PLAN §5 forbids one site from
referencing another site's files, so anything two sites share lives in
`common/`. Nothing here should ever be flown directly either: `SiteManifest`
identifies a run by the manifest sitting beside the running scene, so a run
launched on a scene in here would record a null `site_id` and be uncitable.

## Why it exists

`s02a_doors_open_a` and `s02c_doors_open_c` are two arms of one experiment. They
have to be identical in every respect except which door opens, and the cheapest
way to guarantee that is for them to be *literally the same geometry* —
instanced, not copied. A copy drifts the first time someone nudges a wall.

| File | What it is |
|---|---|
| `room.tscn` | Environment, lighting, the room (copied verbatim from `s01`), the divider wall at `x = 0` with three 4 × 5 m openings cut in it at `z = -9 / 0 / +9`, the spawn marker and the goal. |
| `room_far_spawn.tscn` | Inherited scene of `room.tscn` that overrides only the `Spawn` marker, moving it to `x = 20`. Used by the "map 2.5" pair `s02va_doors_visible_a` / `s02vc_doors_visible_c`, which need all three doors in frame at the switch. Geometry stays shared with s02a/c. |
| `bank.tscn` | A `TriggeredDoorBank` with `DoorA` / `DoorB` / `DoorC` pre-placed to seal those openings, and the trigger slab at `x = 6.5`. |

The two are a matched pair: the panel positions in the bank are married to the
openings in the room. Move a doorway and the door that seals it has to move with
it, which is why the bank lives here rather than in `common/props/` beside the
generic props — the
*scripts* it uses (`triggered_door.gd`, `triggered_door_bank.gd`) are generic and
do live in `common/props/`, but this particular arrangement of them is site
geometry.

## How a variant uses them

A variant `site.tscn` instances both and overrides exactly one pair of exports
on the bank's root:

```
[node name="ThreeDoorsBank" parent="Props" instance=ExtResource("2_bank")]
doors_to_open = Array[NodePath]([NodePath("DoorA")])
doors_to_close = Array[NodePath]([NodePath("DoorB")])
```

That pair of lines is the entire experimental manipulation. Anything else a
variant needs to change belongs in a new room scene, not in an override here —
a change to a file in this folder changes **both** arms, and both manifests need
a `version` bump when it does.
