// GOLD WATER «Тежам», сцена 3: отец с баклажкой 10 л подходит к аппарату, ставит в нишу, наезд камеры на струю.
// Последний кадр — крупно струя → склейка по совпадению с каплей «Сувнинг йўли».
export const DURATION = 8;

export function build(THREE, scene, K) {
  K.stage(scene);
  // улица: стена магазина за аппаратом, витрина, дверь, бордюр, дерево
  K.box(scene, [9, 3.2, 0.3], [0, 1.6, -0.6], K.COL.env);
  K.box(scene, [2.0, 1.4, 0.05], [-2.4, 1.6, -0.43], 0x7f98a8, { roughness: 0.2, metalness: 0.3 });
  K.box(scene, [1.0, 2.1, 0.06], [2.0, 1.05, -0.43], K.COL.envDark);
  K.box(scene, [9, 0.12, 0.25], [0, 0.06, 4.6], K.COL.envDark);
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.14, 2.6, 12), new THREE.MeshStandardMaterial({ color: 0x6b5a45 }));
  trunk.position.set(3.4, 1.3, 2.2); trunk.castShadow = true; scene.add(trunk);
  const crown = new THREE.Mesh(new THREE.SphereGeometry(1.1, 20, 16), new THREE.MeshStandardMaterial({ color: 0x8aa06a }));
  crown.position.set(3.4, 3.1, 2.2); crown.castShadow = true; scene.add(crown);

  const M = K.machineGoldWater(scene, [0, 0, 0]);
  const man = K.person(scene);
  const can = K.canister(scene);
  const st = K.stream(scene);

  const path = [[0, [-2.4, 0, 4.2]], [3.4, [0.28, 0, 1.0]]];
  const WALK = Math.atan2(2.68, -3.2);
  return {
    update(t) {
      // ходьба 0–3,4 с, потом стоит лицом к аппарату
      const p = K.track(path, t);
      const walking = t < 3.4;
            const turn = K.ease((t - 3.0) / 0.5);
      man.place(p, walking ? K.lerp(WALK, Math.PI, turn) : Math.PI);
      man.walk(t * 7.5, walking ? 1 - K.ease((t - 3.0) / 0.4) : 0);
      // баклажка: в правой руке → в нишу (3,5–4,9 с)
      const k = K.ease((t - 3.5) / 1.4);
      const hand = new THREE.Vector3(0.3, 0.42, 0.02).applyAxisAngle(new THREE.Vector3(0, 1, 0), man.g.rotation.y).add(man.g.position);
      const slot = M.windowWorld.clone().add(new THREE.Vector3(0, 0.0, 0.0));
      can.position.copy(hand.clone().lerp(slot, k));
      can.rotation.y = man.g.rotation.y * (1 - k);
      man.armR.rotation.x = -1.1 * Math.sin(Math.PI * Math.min(Math.max((t - 3.5) / 1.6, 0), 1));
      // струя с 5,1 с: от сопла до горлышка
      const top = M.nozzleWorld; const neck = slot.y + 0.35;
      const len = (top.y - neck) * K.easeOut((t - 5.1) / 0.35);
      st.set(top, t > 5.1 ? len : 0);
    },
  };
}

export function camera(t, K) {
  const pos = K.track([[0, [0.2, 1.65, 8.6]], [3.4, [-1.45, 1.45, 2.4]], [5.0, [-0.95, 1.25, 1.55]], [8.0, [-0.17, 1.17, 0.66]]], t);
  const look = K.track([[0, [-1.9, 1.1, 3.9]], [1.8, [-0.9, 1.1, 2.4]], [3.4, [-0.05, 1.0, 0.4]], [5.0, [-0.1, 1.0, 0.3]], [8.0, [-0.1, 1.16, 0.2]]], t);
  const fov = K.lerp(42, 32, K.ease((t - 5) / 3));
  return { pos, look, fov };
}
