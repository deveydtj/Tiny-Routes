import SceneKit

/// The curved 3D map's "rolling log": the world is laid out, driven and tapped on a
/// flat plane, and only drawn bent. A vertex shader drops every vertex by
/// `curvature × ahead²`, where `ahead` is how far it lies in front of the lens
/// along -z, so the ground rolls away over a near horizon. Nothing bends across x,
/// which keeps the horizon a straight line.
///
/// The lens never moves; the world slides under it like a treadmill. So the bend's
/// origin is a constant, the shadow pass bends exactly as the colour pass does, and
/// no uniform changes from frame to frame.
struct TRCurvedWorld: Equatable {
    /// How far the ground drops per unit of distance ahead, squared.
    let curvature: Double
    /// The world z the bend is measured from: the lens's own.
    let originZ: Double

    /// How far ahead of the bend's origin `z` lies.
    func ahead(_ z: Double) -> Double {
        originZ - z
    }

    /// How far the world has dropped at `z`.
    func drop(atZ z: Double) -> Double {
        let ahead = ahead(z)
        return curvature * ahead * ahead
    }

    /// A flat world point as it's drawn.
    func bent(_ point: SIMD3<Double>) -> SIMD3<Double> {
        SIMD3(point.x, point.y - drop(atZ: point.z), point.z)
    }

    /// A flat world normal at `z` as it's drawn: tipped forwards with the slope.
    func bentNormal(_ normal: SIMD3<Double>, atZ z: Double) -> SIMD3<Double> {
        // y' = y − c·d² gives ∂y'/∂z = 2c·d; normals take the inverse transpose.
        simd_normalize(SIMD3(normal.x, normal.y, normal.z - 2 * curvature * ahead(z) * normal.y))
    }

    /// Whether a point `height` over the ground at `z` shows over the curve to an
    /// eye `eyeHeight` above the ground at the bend's origin. The ground ahead is the
    /// cap y = −c·D²; the sight line from the eye to the point dips under it, and the
    /// point is hidden, when its slope s satisfies s² > 4·c·eyeHeight with its lowest
    /// gap to the cap between the two.
    func isVisible(height: Double, atZ z: Double, eyeHeight: Double) -> Bool {
        let distance = ahead(z)
        guard distance > 0 else { return true }
        let slope = (height - drop(atZ: z) - eyeHeight) / distance
        // Where the gap between sight line and ground is smallest.
        let closest = -slope / (2 * curvature)
        guard closest > 0, closest < distance else { return true }
        return slope * slope <= 4 * curvature * eyeHeight
    }

    // MARK: - SceneKit

    /// The bend, in world space. Normals tip with the slope so the far side of the
    /// log turns from the sun.
    static let shaderModifier = """
        #pragma arguments
        float curvedWorldCurvature;
        float curvedWorldOriginZ;
        #pragma body
        float4 world = scn_node.modelTransform * _geometry.position;
        float ahead = curvedWorldOriginZ - world.z;
        world.y -= curvedWorldCurvature * ahead * ahead;
        _geometry.position = scn_node.inverseModelTransform * world;
        float3 normal = (scn_node.modelTransform * float4(_geometry.normal, 0.0)).xyz;
        normal.z -= 2.0 * curvedWorldCurvature * ahead * normal.y;
        _geometry.normal = normalize((scn_node.inverseModelTransform * float4(normal, 0.0)).xyz);
        """

    /// Bends everything under `root`. Geometry and materials are copied first, since
    /// the diorama's pieces share theirs with the gameplay table, which stays flat;
    /// what was shared under `root` stays shared, so each material compiles once.
    @MainActor
    func install(on root: SCNNode) {
        // Originals are kept alive with their copies, so no identifier is reused.
        var geometries: [ObjectIdentifier: (original: SCNGeometry, bent: SCNGeometry)] = [:]
        var materials: [ObjectIdentifier: (original: SCNMaterial, bent: SCNMaterial)] = [:]
        root.enumerateHierarchy { node, _ in
            guard let geometry = node.geometry else { return }
            if let cached = geometries[ObjectIdentifier(geometry)] {
                node.geometry = cached.bent
                return
            }
            guard let copy = geometry.copy() as? SCNGeometry else { return }
            copy.materials = geometry.materials.map { material in
                if let cached = materials[ObjectIdentifier(material)] { return cached.bent }
                let bent = bentCopy(of: material)
                materials[ObjectIdentifier(material)] = (material, bent)
                return bent
            }
            geometries[ObjectIdentifier(geometry)] = (geometry, copy)
            node.geometry = copy
        }
    }

    @MainActor
    private func bentCopy(of material: SCNMaterial) -> SCNMaterial {
        let bent = material.copy() as? SCNMaterial ?? material
        var modifiers = bent.shaderModifiers ?? [:]
        assert(modifiers[.geometry] == nil, "A curved-world material already moves its vertices")
        modifiers[.geometry] = Self.shaderModifier
        bent.shaderModifiers = modifiers
        // Metal takes the arguments as floats.
        bent.setValue(Float(curvature), forKey: "curvedWorldCurvature")
        bent.setValue(Float(originZ), forKey: "curvedWorldOriginZ")
        return bent
    }
}
