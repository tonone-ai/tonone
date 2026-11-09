const tile =
  "flex size-12 items-center justify-center rounded-xl bg-indigo-100";
export const Features = () => (
  <div className="grid grid-cols-3 gap-6">
    <div>
      <div className="flex size-12 items-center justify-center rounded-xl bg-indigo-100">
        <Zap />
      </div>
      <h3>Fast</h3>
    </div>
    <div>
      <div className="flex size-12 items-center justify-center rounded-xl bg-indigo-100">
        <Lock />
      </div>
      <h3>Safe</h3>
    </div>
    <div>
      <div className="flex size-12 items-center justify-center rounded-xl bg-indigo-100">
        <Cog />
      </div>
      <h3>Simple</h3>
    </div>
  </div>
);
