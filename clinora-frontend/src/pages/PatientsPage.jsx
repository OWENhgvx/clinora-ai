import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  AmbientBlobs,
  IllustBranch,
  IllustFlower,
} from "../components/illustrations";
import { FormField, InkDivider } from "../components/ui";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { fmtD } from "../core/utils";

export default function PatientsPage({ api, onStartConsult }) {
  const { t } = useTranslation();
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editP, setEditP] = useState(null);
  const blank = {
    name: "",
    dob: "",
    gender: "",
    blood_type: "",
    allergies: "",
    medications: "",
    conditions: "",
    notes: "",
  };
  const [form, setForm] = useState(blank);
  const [saving, setSaving] = useState(false);
  const [selP, setSelP] = useState(null);
  const [pSess, setPSess] = useState([]);
  const ff = (k) => (v) => setForm((p) => ({ ...p, [k]: v }));

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setPatients(await api.patients());
    } catch {}
    setLoading(false);
  }, [api]);

  useEffect(() => {
    load();
  }, [load]);

  async function save() {
    setSaving(true);
    try {
      if (editP) {
        await api.updatePatient(editP.id, form);
      } else {
        await api.createPatient(form);
      }
      await load();
      setShowForm(false);
      setEditP(null);
      setForm(blank);
    } catch (e) {
      alert(e.message);
    }
    setSaving(false);
  }

  async function del(id) {
    if (!confirm(t("patients.delete_confirm"))) return;
    await api.deletePatient(id);
    load();
  }

  async function pick(p) {
    if (selP?.id === p.id) {
      setSelP(null);
      setPSess([]);
      return;
    }
    setSelP(p);
    try {
      setPSess(await api.patientSessions(p.id));
    } catch {}
  }

  function startEdit(p) {
    setEditP(p);
    setForm({
      name: p.name,
      dob: p.dob || "",
      gender: p.gender || "",
      blood_type: p.blood_type || "",
      allergies: p.allergies || "",
      medications: p.medications || "",
      conditions: p.conditions || "",
      notes: p.notes || "",
    });
    setShowForm(true);
  }

  const genderEmoji = (g) =>
    g === "Male" ? "👨" : g === "Female" ? "👩" : "🧑";
  const bgColors = [
    "linear-gradient(135deg,var(--rosePale),var(--amberPale))",
    "linear-gradient(135deg,var(--sagePale),var(--navyPale))",
    "linear-gradient(135deg,var(--amberPale),var(--goldPale))",
    "linear-gradient(135deg,var(--navyPale),var(--plumPale))",
  ];

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--paper)",
        paddingTop: 72,
        paddingBottom: 56,
        position: "relative",
        zIndex: 1,
        overflow: "hidden",
      }}
    >
      <AmbientBlobs />
      <IllustBranch
        w={190}
        h={124}
        style={{
          position: "fixed",
          bottom: "6%",
          right: "-1%",
          animation: "float3 10s ease-in-out infinite",
          pointerEvents: "none",
          transform: "scaleX(-1)",
        }}
        opacity={0.13}
      />
      <div
        style={{
          maxWidth: 1080,
          margin: "0 auto",
          padding: "28px 28px 0",
          position: "relative",
          zIndex: 1,
        }}
      >
        <div
          className="fade-up"
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            marginBottom: 28,
            flexWrap: "wrap",
            gap: 18,
          }}
        >
          <div>
            <div className="eyebrow">{t("patients.eyebrow")}</div>
            <h2
              style={{
                fontFamily: "var(--serif)",
                fontSize: 56,
                fontWeight: 400,
                color: "var(--ink)",
                letterSpacing: -1.2,
                lineHeight: 0.9,
              }}
            >
              {t("patients.title").split(" ")[0]}
              <br />
              <span className="grad-heading">
                {t("patients.title").split(" ").slice(1).join(" ")}
              </span>
            </h2>
            <p
              style={{
                fontFamily: "var(--body)",
                fontSize: 15,
                color: "var(--ink4)",
                marginTop: 10,
              }}
            >
              {t("patients.count", { count: patients.length })}
            </p>
          </div>
          <Button
            onClick={() => {
              setShowForm(true);
              setEditP(null);
              setForm(blank);
            }}
            size="lg"
          >
            {t("patients.new")}
          </Button>
        </div>
        <div className="gold-rule" style={{ marginBottom: 24 }} />

        {showForm && (
          <div
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(22,15,6,0.62)",
              zIndex: 200,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 24,
              backdropFilter: "blur(6px)",
            }}
            onClick={(e) => e.target === e.currentTarget && setShowForm(false)}
          >
            <div
              className="card scale-in"
              style={{
                width: "100%",
                maxWidth: 530,
                maxHeight: "90vh",
                overflowY: "auto",
                boxShadow: "var(--shadow-xl)",
                padding: "34px 38px",
              }}
            >
              <div className="shine" />
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  marginBottom: 20,
                }}
              >
                <div>
                  <p
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 10,
                      color: "var(--ink5)",
                      letterSpacing: "0.16em",
                      marginBottom: 5,
                    }}
                  >
                    {editP ? t("patients.edit_title") : t("patients.new_title")}
                  </p>
                  <h3
                    style={{
                      fontFamily: "var(--serif)",
                      fontSize: 24,
                      fontWeight: 400,
                      fontStyle: "italic",
                      color: "var(--ink)",
                    }}
                  >
                    {editP
                      ? t("patients.update_btn")
                      : t("patients.create_btn")}
                  </h3>
                </div>
                <Button
                  onClick={() => setShowForm(false)}
                  variant="ghost"
                  size="icon-sm"
                >
                  ×
                </Button>
              </div>
              <InkDivider style={{ margin: "0 0 18px" }} />
              <FormField
                label={t("patients.field_name")}
                value={form.name}
                onChange={ff("name")}
                placeholder={t("patients.placeholder_name")}
              />
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 14,
                }}
              >
                <div style={{ marginBottom: 16 }}>
                  <label className="ink-label">{t("patients.field_dob")}</label>
                  <Input
                    type="date"
                    value={form.dob}
                    onChange={(e) => ff("dob")(e.target.value)}
                    className="h-[46px]"
                    style={{ fontFamily: "var(--body)" }}
                  />
                </div>
                <div style={{ marginBottom: 16 }}>
                  <label className="ink-label">
                    {t("patients.field_gender")}
                  </label>
                  <Select
                    value={form.gender}
                    onValueChange={(v) => ff("gender")(v)}
                  >
                    <SelectTrigger style={{ fontFamily: "var(--body)" }}>
                      <SelectValue placeholder="—" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Male">
                        {t("patients.gender_male")}
                      </SelectItem>
                      <SelectItem value="Female">
                        {t("patients.gender_female")}
                      </SelectItem>
                      <SelectItem value="Other">
                        {t("patients.gender_other")}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <FormField
                label={t("patients.field_blood")}
                value={form.blood_type}
                onChange={ff("blood_type")}
                placeholder={t("patients.placeholder_blood")}
              />
              <FormField
                label={t("patients.field_allergies")}
                value={form.allergies}
                onChange={ff("allergies")}
                placeholder={t("patients.placeholder_allergies")}
              />
              <FormField
                label={t("patients.field_medications")}
                value={form.medications}
                onChange={ff("medications")}
                placeholder={t("patients.placeholder_medications")}
              />
              <FormField
                label={t("patients.field_conditions")}
                value={form.conditions}
                onChange={ff("conditions")}
                placeholder={t("patients.placeholder_conditions")}
              />
              <FormField
                label={t("patients.field_notes")}
                value={form.notes}
                onChange={ff("notes")}
                placeholder={t("patients.placeholder_notes")}
              />
              <div style={{ display: "flex", gap: 10, marginTop: 6 }}>
                <Button
                  onClick={() => setShowForm(false)}
                  variant="outline"
                  size="lg"
                  className="flex-1"
                >
                  {t("patients.cancel")}
                </Button>
                <Button
                  onClick={save}
                  disabled={!form.name.trim() || saving}
                  size="lg"
                  className="flex-[2]"
                >
                  {saving
                    ? t("patients.saving")
                    : editP
                      ? t("patients.save")
                      : t("patients.create")}
                </Button>
              </div>
            </div>
          </div>
        )}

        {loading ? (
          <div
            style={{
              textAlign: "center",
              padding: 80,
              fontFamily: "var(--body)",
              fontStyle: "italic",
              color: "var(--ink4)",
              fontSize: 17,
            }}
          >
            {t("patients.loading")}
          </div>
        ) : patients.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "80px 40px",
              border: "1.5px dashed rgba(22,15,6,0.18)",
              borderRadius: 6,
            }}
          >
            <IllustFlower
              size={90}
              opacity={0.28}
              color="var(--rose)"
              style={{ margin: "0 auto 18px" }}
            />
            <p
              style={{
                fontFamily: "var(--serif)",
                fontSize: 24,
                fontStyle: "italic",
                color: "var(--ink3)",
              }}
            >
              {t("patients.empty")}
            </p>
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill,minmax(294px,1fr))",
              gap: 13,
            }}
          >
            {patients.map((p, i) => (
              <div
                key={p.id}
                className="card fade-up"
                style={{
                  animationDelay: `${i * 0.05}s`,
                  overflow: "hidden",
                  borderColor: selP?.id === p.id ? "var(--rose)" : undefined,
                }}
              >
                <div className="shine" />
                <div
                  style={{
                    height: 8,
                    background: bgColors[i % bgColors.length],
                  }}
                />
                <div
                  onClick={() => pick(p)}
                  style={{ padding: "18px 20px", cursor: "pointer" }}
                >
                  <div style={{ display: "flex", gap: 13, marginBottom: 12 }}>
                    <div
                      style={{
                        width: 50,
                        height: 50,
                        borderRadius: 14,
                        background: bgColors[i % bgColors.length],
                        border: "1px solid rgba(22,15,6,0.08)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 26,
                        flexShrink: 0,
                        boxShadow: "var(--shadow-sm)",
                        animation:
                          selP?.id === p.id
                            ? "pulse 2s ease-in-out infinite"
                            : "none",
                      }}
                    >
                      {genderEmoji(p.gender)}
                    </div>
                    <div>
                      <p
                        style={{
                          fontFamily: "var(--serif)",
                          fontSize: 17,
                          fontStyle: "italic",
                          color: "var(--ink)",
                          fontWeight: 400,
                        }}
                      >
                        {p.name}
                      </p>
                      <div
                        style={{
                          display: "flex",
                          gap: 5,
                          marginTop: 4,
                          flexWrap: "wrap",
                        }}
                      >
                        {p.gender && (
                          <Badge className="px-2 py-0 text-[9px]">
                            {p.gender}
                          </Badge>
                        )}
                        {p.blood_type && (
                          <Badge
                            variant="rose"
                            className="px-2 py-0 text-[9px]"
                          >
                            {p.blood_type}
                          </Badge>
                        )}
                        {p.dob && (
                          <Badge className="px-2 py-0 text-[9px]">
                            {new Date(p.dob).getFullYear()}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  {p.conditions && (
                    <p
                      style={{
                        fontFamily: "var(--body)",
                        fontSize: 12.5,
                        color: "var(--ink4)",
                        fontStyle: "italic",
                        lineHeight: 1.5,
                      }}
                    >
                      {p.conditions.slice(0, 72)}
                      {p.conditions.length > 72 ? "…" : ""}
                    </p>
                  )}
                </div>
                <div
                  style={{
                    borderTop: "1px solid rgba(22,15,6,0.08)",
                    padding: "9px 16px",
                    display: "flex",
                    gap: 7,
                  }}
                >
                  <Button
                    onClick={() => onStartConsult(p)}
                    size="xs"
                    className="flex-1"
                  >
                    {t("patients.consult")}
                  </Button>
                  <Button
                    onClick={() => startEdit(p)}
                    variant="outline"
                    size="xs"
                  >
                    {t("common.edit")}
                  </Button>
                  <Button onClick={() => del(p.id)} variant="danger" size="xs">
                    {t("common.delete")}
                  </Button>
                </div>
                {selP?.id === p.id && pSess.length > 0 && (
                  <div
                    className="scale-in"
                    style={{
                      borderTop: "1px solid rgba(22,15,6,0.08)",
                      padding: "12px 18px",
                      background: "var(--paper3)",
                    }}
                  >
                    <p className="ink-label" style={{ marginBottom: 8 }}>
                      {t("patients.sessions_count", { count: pSess.length })}
                    </p>
                    {pSess.slice(0, 3).map((s) => (
                      <div key={s.id} style={{ marginBottom: 8 }}>
                        <p
                          style={{
                            fontFamily: "var(--body)",
                            fontSize: 12.5,
                            color: "var(--ink3)",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            fontStyle: "italic",
                          }}
                        >
                          {s.description}
                        </p>
                        <p
                          style={{
                            fontFamily: "var(--mono)",
                            fontSize: 9,
                            color: "var(--ink5)",
                          }}
                        >
                          {fmtD(s.created_at)}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
