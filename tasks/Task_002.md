# Task_002 — Validate equations and simulation contracts

## Scope

Verify the square-plate and circular-plate equations against 2–3 authoritative sources, resolve notation/parameter decisions, and define the reviewed contracts needed by later implementation tasks.

## Owner decisions required before Task_002 can pass

These are open specification questions, not settled implementation statements. The coordinator will record your answers and the three specialists will review the resulting contract.

## Owner decisions recorded

- Use a normalized visual modal approximation, not a full elastic-plate solver.
- Use centered coordinates `[-1, 1] × [-1, 1]` for the square model.
- `n` and `m` are integer modes; `(n,m)` and `(m,n)` are canonicalized to one representation.
- Use a fixed-rim circular condition.
- The Engineer will recommend the circular coefficient/order/root ranges, subject to Architect and QA review.
- Use SciPy for Bessel evaluation.
- Presets may use a lookup table; dynamic microphone frequency calculates visual motion. Silence, out-of-bounds, or errored data leaves the program running and retains the last valid behavior until new valid data arrives.
- Manual mode exposes frequency and volume controls.
- Audio state is represented by an immutable latest-value snapshot; snapshots are not cached or accumulated.
- Microphone-off mode produces audible sine playback at the selected frequency. Playback stops when the microphone is enabled or volume is reduced to zero.
- Golden coordinates are required for the 1–12 layouts and the brief selection pause/commit behavior.
- QA owns the equation and FFT test strategy, including tolerances, subject to the approved contracts.
- Particle boundary behavior uses reflection: an out-of-bounds coordinate is mirrored at the drawable boundary and the corresponding motion component reverses sign, preserving the particle inside the drawable region.

The particle boundary decision is now resolved as reflection rather than clamp, wrap, or retain-last-valid.

1. **Physical model:** Should this project implement normalized visual modal fields based on the project-plan equations, explicitly labeled as an approximation, or should it implement a full elastic-plate model with plate-specific boundary conditions?
2. **Square coordinates:** Should the square evaluator use normalized coordinates `[0, 1] × [0, 1]` or centered coordinates `[-1, 1] × [-1, 1]`? Which direction should screen Y map to, and are boundary points included?
3. **Square modes:** Should `n` and `m` each be limited to integers `1–8` as suggested by the plan? Should `n == m` be accepted as a zero/trivial field, and should `(n,m)` and `(m,n)` be canonicalized?
4. **Circular boundary model:** Should the circular evaluator use a fixed-rim condition with positive zeros of `J_order`, as the current plan implies? Or should a different rim/center condition be used?
5. **Circular parameters:** What ranges should be allowed for Bessel order, radial-root index, cosine coefficient, and sine coefficient? Should the all-zero coefficient pair be rejected?
6. **Numerical dependency:** Do you approve adding a pinned SciPy dependency for `jv` and `jn_zeros`, or should the project use a maintained pure-Python alternative? What should the UI do if the selected dependency is unavailable?
7. **Frequency mapping:** Should microphone/manual frequency select modes through a deterministic lookup table, physically calculate modes from plate/material properties, or only scale visual motion? How should values outside 60–5000 Hz, silence, stale snapshots, and errors behave?
8. **Manual override:** When the microphone is disabled, should manually selected equation parameters completely override frequency-derived modes? Which fields must be editable for each plate shape?
9. **Audio snapshot:** Do you approve an immutable latest-value snapshot containing dominant frequency, amplitude, sequence, monotonic timestamp, and a status such as `ok`, `silent`, `overflow`, `device_error`, or `manual`? If not, what fields/statuses should it contain?
10. **Particle motion:** How should equation value, frequency, amplitude, and timestep combine to update a particle position? Should positions clamp, reflect, wrap, or fall back to the last valid position when evaluation is invalid?
11. **Sine behavior:** Should the sine feature generate deterministic analysis samples only, or should it also produce audible playback? If playback is required, what non-blocking lifecycle and stop behavior are expected?
12. **Layout contract:** What exact drawable bounds, header exclusion, center, radii, and geometric tolerances should define the 1–12 particle layouts? Are the project-plan shape descriptions sufficient, or should golden coordinates be approved?
13. **Test tolerance:** What numerical tolerance should be accepted for equation/FFT tests, and should deterministic scalar tests target approximately `1e-10` when the selected dependency supports it?

## Acceptance criteria

- Equation accuracy is checked against 2–3 authoritative sources and citations are recorded in the task review artifact.
- The square evaluator contract is defined as a pure function over normalized Cartesian coordinates and explicit integer mode parameters; the circular evaluator contract is defined over normalized polar coordinates and explicit Bessel order/root parameters.
- Coordinate conventions, valid parameter ranges, boundary behavior, singular/trivial cases, frequency-to-mode mapping, and numerical fallback behavior are explicitly decided or marked `UNKNOWN — needs human confirmation`.
- The approved equation-parameter schema enumerates every user-adjustable field for square and circular plates, including concrete types, defaults, ranges, validation errors, and serialization/display labels.
- The sine decision explicitly distinguishes deterministic analysis/sample generation from optional audible playback; playback is not included unless separately approved with a non-blocking lifecycle contract.
- The dependency decision for Bessel evaluation is verified: installed package, exact version, import path, clean-install requirement, and fallback/error behavior. No dependency is added without review approval.
- Contracts are specified with inputs, outputs, errors, lifecycle, and concurrency semantics for `Settings`, `particle_layout(count, width, height)`, equation evaluators, `AudioSnapshot`, and particle workers.
- At least two deterministic equation vectors per plate, boundary tests, invalid-parameter tests, and symmetry/trivial-case tests are defined with tolerances.
- Decisions are recorded in the living-memory docs with invariants, blast radius, verification basis, and freshness notes.
- No implementation code is written until unanimous review approval.

## Proposed contract pending owner approval

The Engineer proposes the following concrete baseline for review:

### Coordinates and equations

- Square evaluator inputs are centered `x,y ∈ [-1,1]`; convert to equation coordinates with `u=(x+1)/2`, `v=(y+1)/2`.
- Screen Y is inverted when mapped to centered coordinates; both drawable boundaries are inclusive.
- `square_value(x,y,n,m)` uses integer modes `1..8`, canonicalized as `(min(n,m),max(n,m))`; equal modes are valid and return the zero field.
- Circular inputs are `r ∈ [0,1]`, `theta ∈ [-π,π)`, with a fixed rim. Use `jv(order, k*r)` and `jn_zeros(order, root_index)`, with proposed `order 0..8`, `root_index 1..8`, and cosine/sine weights each in `[-1,1]`. Reject both weights being zero and normalize the weight vector.
- These are normalized visual modal approximations, not a full elastic-plate solver.

### Motion and reflection

Particles store pixel position, velocity, anchor, and last-valid position. Proposed update:

```text
field_norm = clamp(field_value / field_scale, -1, 1)
frequency_norm = clamp((frequency_hz - 60) / 4940, 0, 1)
speed = 60 + 180 * frequency_norm
delta = radial_direction(anchor - center) * speed * volume * field_norm * dt
candidate = position + velocity * dt + delta
```

`dt` is monotonic and clamped to `[0,0.1]`. Candidate positions reflect across drawable boundaries using a folded interval of period `2*(hi-lo)`, including arbitrary overshoot and corner collisions; odd reflections reverse the corresponding velocity component. Non-finite values retain the last-valid position and velocity.

### Audio snapshot and playback

Proposed immutable latest-only schema:

```text
AudioSnapshot(
  frequency_hz: float,
  amplitude: float,       # 0..1
  volume: float,           # 0..1
  sequence: int,
  timestamp_monotonic: float,
  status: ok|manual|silent|stale|overflow|device_error,
)
```

Publish one lock-protected current value only; retain no history or raw buffers. Sequence numbers increase monotonically and snapshots older than 0.25 seconds become stale. Silent/stale/overflow/device-error states retain the last valid simulation behavior until valid data arrives.

Manual sine playback is proposed through `pygame.mixer`: 48 kHz, mono, signed 16-bit, 512-sample chunks, volume `[0,1]`. It starts only in microphone-off mode with nonzero volume, stops idempotently when microphone mode is enabled or volume reaches zero, and continues manual visual simulation if mixer startup fails. Mixer ownership remains on the Pygame/UI thread and shutdown occurs before `pygame.quit()`.

### Dependencies and fixtures

Proposed pins are `scipy==1.18.1` and `numpy==2.2.6`, verified through a Python 3.12 clean-install check before dependency changes are made. Circular mode reports an explicit unavailable state if SciPy cannot import; it does not silently substitute another equation.

Golden layout fixtures will use drawable rectangle `x=32..768`, `y=112..584`, center `(400,348)`, and exact ordered integer coordinate arrays for counts 1–12. Fixtures are independent test data, not generated by the implementation under test; alternate dimensions also test count, bounds, and arrangement invariants.

### Owner approval gate

Please approve or request changes to this proposed contract. The Engineer will own the circular parameter recommendation, QA will own equation/FFT tolerances and test vectors, and no downstream implementation task will start until the three agents approve the recorded contract.

**Owner approval:** Approved by the user after review of the proposed contract.

## Resolved contract details

The following implementation details are now fixed for downstream tasks:

- Defaults: square mode `(n,m)=(1,2)`, circular `(order,root_index)=(0,1)`, circular weights `(1.0,0.0)`, frequency `440 Hz`, manual volume `0.5`.
- Centered square inputs are mapped with `u=(x+1)/2`, `v=(y+1)/2` and evaluated as `cos(nπu)cos(mπv) - cos(mπu)cos(nπv)`. Canonicalization stores `(min(n,m),max(n,m))`; the canonical scalar is used consistently, so callers do not depend on the sign change from swapping modes.
- Circular evaluation uses `k=jn_zeros(order,root_index)[root_index-1]`, `J_order(k*r) * (c*cos(order*theta)+s*sin(order*theta))`, with the coefficient vector normalized to unit length after rejecting `(c,s)=(0,0)`. `theta` is ignored at `r=0`; `r=1` is a fixed-rim zero within tolerance.
- Particle motion is persistent-velocity based: on each update, compute `target_velocity=radial_direction(anchor-center)*speed*volume*field_norm`, move with `candidate=position+velocity*dt`, then blend velocity toward `target_velocity` with a fixed critically-damped factor `alpha=min(1,dt*12)`. `field_norm=clamp(field_value/field_scale,-1,1)`, `frequency_norm=clamp((frequency_hz-60)/4940,0,1)`, and `speed=60+180*frequency_norm`. `field_scale` is `2.0` for square and `1.0` for circular; zero-length radial direction uses `(1,0)`; `dt` is clamped to `[0,0.1]` seconds. Reflected velocity remains authoritative after a boundary hit and is blended toward the next target over later updates, so a reflection cannot be overwritten immediately.
- Reflection applies to candidate position and velocity using a folded interval of period `2*(hi-lo)` for each axis. Multiple crossings are handled by modulo/folding; each odd fold reverses that axis velocity. Drawable bounds include the hollow-marker radius, and corners reflect independently on both axes. Non-finite values retain last-valid position and velocity.
- Dynamic microphone frequency and manual frequency affect motion speed and sine playback frequency; they do not silently change equation modes. Manual equation fields remain authoritative when microphone mode is disabled.
- The immutable snapshot is a single lock-protected current value with fields `frequency_hz: float`, `amplitude: float`, `volume: float`, `sequence: int`, `timestamp_monotonic: float`, and status enum `ok|manual|silent|stale|overflow|device_error`. There is no history/raw-buffer cache. Sequence starts at `0` and increments on each publication; snapshots older than `0.25s` are interpreted as stale. Simulation state, not the producer, owns last-valid motion behavior.
- The audio component owns sample generation and state; the Pygame/UI thread owns all `pygame.mixer` calls. Playback uses 48 kHz mono signed 16-bit 512-sample chunks, volume `[0,1]`, idempotent start/stop, and stops before `pygame.quit()`.
- The dependency gate passed on Python 3.12.10 with `numpy==2.2.6`, `scipy==1.18.1`, and `from scipy.special import jv, jn_zeros`; the verified Bessel root `jn_zeros(0,1)[0]` was `2.4048255576957724`. If SciPy import fails, circular mode reports an explicit unavailable state.
- Golden layouts use `x=32..768`, `y=112..584`, center `(400,348)`, exact ordered fixtures for counts 1–12, and independent expected data. Selection publishes a pending fixture, pauses updates, commits atomically, then resumes. Alternate dimensions test cardinality, bounds, and arrangement invariants.

## Settings and layout contracts

`Settings` is an immutable/transactionally-updated value object with these fields and defaults: `brush_size:int=5` (1..50), `brush_color:tuple[int,int,int]=(0,0,0)` (each 0..255), `brush_style:str="round"` (approved values `round|square`), `particle_count:int=1` (1..12), `microphone_enabled:bool=True`, `frequency_hz:float=440.0` (60..5000), `volume:float=0.5` (0..1), `plate_shape:str="square"` (`square|circular`), `square_n:int=1`, `square_m:int=2`, `circular_order:int=0`, `circular_root_index:int=1`, `circular_cosine_weight:float=1.0`, and `circular_sine_weight:float=0.0`. Invalid values raise stable `SettingsValidationError` categories (`type`, `range`, `enum`, `finite`, `dependency`) without partial mutation. Serialization uses these exact field names; UI labels are human-readable versions of them.

`particle_layout(count,width,height)` returns an ordered immutable tuple of exactly `count` `(x,y)` pixel coordinates inside the drawable rectangle after marker-radius inset. The canonical 800×600 fixture uses header exclusion `y<112`, drawable bounds `x=32..768`, `y=112..584`, center `(400,348)`, and deterministic ring phase/order. The fixture data is independent of the implementation under test; alternate dimensions verify scaling, cardinality, and arrangement invariants. Layout selection exposes `pending` and `committed` states, pauses simulation while pending, and commits atomically.

## Equation research record

- [Paul Bourke, Chladni plate interference surfaces](https://paulbourke.net/geometry/chladni/) gives the square nodal expression `cos(nπx/L)cos(mπy/L) - cos(mπx/L)cos(nπy/L)=0`, identifies integer modes, and notes the trivial/equivalent behavior for equal/swapped modes.
- [NTHU Physics Laboratory standing-wave notes](https://www.phys.nthu.edu.tw/~gplab/file/07%20Standing%20Waves/07%20Standing%20Waves%20V2.pdf) independently reproduces the square expression and its nodal-pattern interpretation.
- [University of Pennsylvania circular membrane notes](https://www2.math.upenn.edu/~chai/240s05/240hws05/cir_mem.pdf) derives finite-at-center Bessel solutions and fixed-boundary conditions from positive zeros.
- [NIST DLMF §10.2](https://dlmf.nist.gov/10.2) defines `J_ν`, and [DLMF §10.21](https://dlmf.nist.gov/10.21) defines positive Bessel zeros and distinguishes zero families.
- [SciPy `jn_zeros` documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.jn_zeros.html) and [SciPy `jv` documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.jv.html) verify the selected numerical APIs.

These sources support the selected normalized visual modal approximation. They do not establish a full elastic free-edge plate solver; the implementation must keep that limitation visible in its documentation and UI wording.

## Required deterministic vectors

- `square_value(0,0,1,2) == 0.0`.
- `square_value(0.5,0.5,1,2) == 0.0` because centered `(0.5,0.5)` maps to `(u,v)=(0.75,0.75)` and is a nodal point under the selected formula.
- `square_value(-0.75,-0.5,1,2) == -0.5`.
- `square_value(0,0.5,1,2) == -0.7071067811865475` within tolerance.
- `square_value(x,y,n,n) == 0.0` for valid inputs.
- `circular_value(0,0,0,1,1,0) == 1.0`.
- `circular_value(1,0,0,1,1,0)` is approximately `0.0`.
- `circular_value(0.5,0,0,1,1,0)` is approximately `0.669929739`.
- Scalar equation tests use `1e-10` tolerance; FFT/frequency tests use `1e-6` unless QA records a justified alternative.

## Golden 800×600 layout fixtures

The canonical ordered expected coordinates are:

```text
1:  [(400,206)]
2:  [(400,206),(400,490)]
3:  [(400,206),(591,419),(209,419)]
4:  [(556,448),(244,448),(244,248),(556,248)]
5:  [(400,206),(610,304),(530,463),(270,463),(190,304)]
6:  [(400,206),(591,277),(591,419),(400,490),(209,419),(209,277)]
7:  [(400,206),(591,277),(591,419),(400,490),(209,419),(209,277),(400,348)]
8:  [(400,206),(556,248),(621,348),(556,448),(400,490),(244,448),(179,348),(244,248)]
9:  [(400,206),(610,304),(530,463),(270,463),(190,304),(478,398),(322,398),(322,298),(478,298)]
10: [(400,206),(610,304),(530,463),(270,463),(190,304),(400,277),(505,326),(465,405),(335,405),(295,326)]
11: [(400,206),(591,277),(591,419),(400,490),(209,419),(209,277),(400,277),(505,326),(465,405),(335,405),(295,326)]
12: [(556,448),(244,448),(244,248),(556,248),(544,348),(400,440),(256,348),(400,256),(447,378),(353,378),(353,318),(447,318)]
```

The first 2–8 fixtures use the approved outer ring phases; 9–11 use the approved outer/inner ring families; 12 uses outer-square, middle-diamond, inner-square layers. These arrays are independent expected test data.

## Invalid and boundary vectors

- `square_value(x,y,0,1)`, `square_value(x,y,1,9)`, non-finite coordinates, or coordinates outside `[-1,1]` raise `ValueError`.
- `circular_value(r,theta,-1,1,1,0)`, root index `0`/`9`, `r<0`/`r>1`, non-finite values, or both weights zero raise `ValueError`.
- With marker-radius-inset bounds `x=[38,762]`, `y=[118,578]`, candidate `(780,300)` reflects to `(744,300)` and reverses `vx`; candidate `(400,600)` reflects to `(400,556)` and reverses `vy`; candidate `(780,600)` reflects to `(744,556)` and reverses both components. Large overshoots use the same folded-interval rule and never loop unboundedly.
- A non-finite field, target velocity, or candidate retains the last-valid position and velocity and publishes a non-fatal error status.

## Status

Complete — owner-approved and unanimously reviewed. See `docs/reviews/Review-Task-002.md`.
