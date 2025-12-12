import bpy


def shift_armature_keyframes_back_and_update_range(shift=-1):
    obj = bpy.context.object

    if obj is None or obj.type != 'ARMATURE':
        print("Select an armature object first.")
        return

    ad = obj.animation_data
    if ad is None:
        print("Selected armature has no animation data.")
        return

    actions = set()

    # Gather actions
    if ad.action:
        actions.add(ad.action)
    if ad.nla_tracks:
        for track in ad.nla_tracks:
            for strip in track.strips:
                if strip.action:
                    actions.add(strip.action)

    # Track min/max frames
    min_frame = float("inf")
    max_frame = float("-inf")

    # Shift keyframes
    for act in actions:
        for fcurve in act.fcurves:
            for kp in fcurve.keyframe_points:
                # Shift
                kp.co.x += shift
                kp.handle_left.x += shift
                kp.handle_right.x += shift

                # Track new range
                min_frame = min(min_frame, kp.co.x)
                max_frame = max(max_frame, kp.co.x)

    # Update scene range
    scene = bpy.context.scene
    scene.frame_start = int(min_frame)
    scene.frame_end = int(max_frame)

    print(f"Shifted keyframes by {shift} frame(s). New range: {scene.frame_start}–{scene.frame_end}")


# Run it:
shift_armature_keyframes_back_and_update_range(shift=-1)