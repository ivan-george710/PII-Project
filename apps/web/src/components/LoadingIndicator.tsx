import {
  Component,
  lazy,
  Suspense,
  useEffect,
  useState,
  type ReactNode,
} from "react";
const Strands = lazy(() => import("./Strands.jsx"));
class AnimationFallback extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <span className="strands-static" />
    ) : (
      this.props.children
    );
  }
}
export function LoadingIndicator({ label = "Loading…" }: { label?: string }) {
  const [animate, setAnimate] = useState(false);
  useEffect(() => {
    const media = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    const update = () =>
      setAnimate(
        !media?.matches && typeof WebGL2RenderingContext !== "undefined",
      );
    update();
    media?.addEventListener("change", update);
    return () => media?.removeEventListener("change", update);
  }, []);
  return (
    <div className="loading-indicator" role="status">
      <span className="strands-mini" aria-hidden="true">
        <AnimationFallback>
          {animate ? (
            <Suspense fallback={<span className="strands-static" />}>
              <Strands
                colors={["#ffffff", "#999999"]}
                speed={0.35}
                count={4}
                style={{}}
                glow={0.15}
                intensity={0.65}
                saturation={0}
              />
            </Suspense>
          ) : (
            <span className="strands-static" />
          )}
        </AnimationFallback>
      </span>
      <span>{label}</span>
    </div>
  );
}
