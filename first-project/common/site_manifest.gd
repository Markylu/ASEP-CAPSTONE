extends RefCounted
class_name SiteManifest

## Reads the `site.json` sitting next to the running scene.
##
## A run is only citable if it says which site it flew and at which version —
## `s01@v1` has to mean one fixed piece of geometry forever (notes/PLAN.md §5.1).
## Rather than hand-copying the ID into the scene, where it would rot, the site
## folder IS the identity: whatever `site.tscn` is running, its sibling
## `site.json` describes it.
##
## `main.tscn` has no sibling manifest, so it loads empty and the run records a
## null site_id — which correctly says "flown on the unmigrated sandbox".

const FILENAME := "site.json"

var data: Dictionary = {}
var path: String = ""
var errors: PackedStringArray = PackedStringArray()


static func for_current_scene(tree: SceneTree) -> SiteManifest:
	var scene := tree.current_scene
	var scene_path := scene.scene_file_path if scene != null else ""
	return SiteManifest.new().load_beside(scene_path)


func load_beside(scene_path: String) -> SiteManifest:
	if scene_path == "":
		return self
	path = scene_path.get_base_dir().path_join(FILENAME)
	if not FileAccess.file_exists(path):
		path = ""
		return self
	var text := FileAccess.get_file_as_string(path)
	var parsed: Variant = JSON.parse_string(text)
	if not (parsed is Dictionary):
		errors.append("%s is not a JSON object" % path)
		return self
	data = parsed as Dictionary
	_validate(scene_path)
	return self


func exists() -> bool:
	return not data.is_empty()


func id() -> Variant:
	return data.get("id")


func version() -> Variant:
	return data.get("version")


func status() -> String:
	return str(data.get("status", ""))


## Loud, not fatal. A bad manifest should not stop a run — but it must not
## quietly mislabel one either, so every problem is printed once at launch.
func _validate(scene_path: String) -> void:
	for key in ["id", "version", "status", "scene"]:
		if not data.has(key):
			errors.append("%s is missing required key '%s'" % [path, key])
	var declared := str(data.get("scene", ""))
	if declared != "" and declared != scene_path:
		# The classic failure: a site copied from _template that still points at
		# the template's scene, so every run is filed under the wrong ID.
		errors.append("%s declares scene '%s' but the running scene is '%s'"
			% [path, declared, scene_path])
	if status() == "deprecated":
		errors.append("%s is deprecated — do not cite runs flown on it" % path)
	for message in errors:
		push_warning("SITE MANIFEST: " + message)
