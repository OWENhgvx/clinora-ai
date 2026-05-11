import { useEffect } from "react";
import { gsap } from "gsap";

export function useAuthGsapIdle(containerRef, blinkRef, lookRef, nodRef) {
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const shadeGroup = el.querySelector("#ag-shade-group");
    const cordEnd = el.querySelector("#ag-cord-end");

    if (shadeGroup) {
      gsap.to(shadeGroup, {
        rotation: 1.4,
        transformOrigin: "-10px -28px",
        duration: 4,
        ease: "sine.inOut",
        yoyo: true,
        repeat: -1,
      });
    }
    if (cordEnd) {
      gsap.to(cordEnd, {
        attr: { transform: "translate(113, 231)" },
        duration: 4.2,
        ease: "sine.inOut",
        yoyo: true,
        repeat: -1,
      });
    }

    function doBlink() {
      const bl = el.querySelector("#ag-blink-l");
      const br = el.querySelector("#ag-blink-r");
      if (!bl || !br) return;
      gsap.to([bl, br], {
        attr: { height: 20, y: -10 },
        duration: 0.07,
        ease: "power2.in",
        onComplete() {
          gsap.to([bl, br], {
            attr: { height: 0 },
            duration: 0.09,
            ease: "power2.out",
            onComplete: scheduleBlink,
          });
        },
      });
    }
    function scheduleBlink() {
      blinkRef.current = setTimeout(
        () => {
          doBlink();
          if (Math.random() < 0.3) setTimeout(doBlink, 220);
        },
        (1.8 + Math.random() * 3.5) * 1000,
      );
    }
    scheduleBlink();

    function doLook() {
      const pl = el.querySelector("#ag-pupil-l");
      const pr = el.querySelector("#ag-pupil-r");
      if (!pl || !pr) return;
      const dx = (Math.random() - 0.5) * 7;
      const dy = (Math.random() - 0.5) * 3;
      gsap.to([pl, pr], {
        x: dx,
        y: dy,
        duration: 0.35,
        ease: "power2.out",
        onComplete() {
          setTimeout(
            () => {
              gsap.to([pl, pr], {
                x: 0,
                y: 0,
                duration: 0.28,
                ease: "power2.inOut",
                onComplete: scheduleLook,
              });
            },
            600 + Math.random() * 1400,
          );
        },
      });
    }
    function scheduleLook() {
      lookRef.current = setTimeout(doLook, (3 + Math.random() * 6) * 1000);
    }
    scheduleLook();

    function scheduleNod() {
      nodRef.current = setTimeout(
        () => {
          if (!shadeGroup) {
            scheduleNod();
            return;
          }
          gsap.to(shadeGroup, {
            rotation: 5,
            transformOrigin: "-10px -28px",
            duration: 0.25,
            ease: "power2.out",
            yoyo: true,
            repeat: 1,
            onComplete: scheduleNod,
          });
        },
        (8 + Math.random() * 10) * 1000,
      );
    }
    scheduleNod();

    return () => {
      if (shadeGroup) gsap.killTweensOf(shadeGroup);
      if (cordEnd) gsap.killTweensOf(cordEnd);
      clearTimeout(blinkRef.current);
      clearTimeout(lookRef.current);
      clearTimeout(nodRef.current);
    };
  }, [containerRef, blinkRef, lookRef, nodRef]);
}
