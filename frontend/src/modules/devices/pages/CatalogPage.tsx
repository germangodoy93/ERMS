import { Check, Pencil, Plus, Power, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { SelectField } from "@/components/SelectField";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { errorMessage } from "@/services/errors";

import {
  useCategories,
  useCreateManufacturer,
  useManufacturers,
  useModels,
  useUpdateManufacturer,
  useUpdateModel,
} from "../hooks";

const ALL = "";

export function CatalogPage() {
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Catálogo de equipos</h1>
        <p className="text-muted-foreground text-sm">
          Fabricantes y modelos. Recepción crea modelos nuevos al registrar equipos; aquí se
          corrigen o se desactivan.
        </p>
      </header>
      <div className="grid gap-6 lg:grid-cols-[22rem_1fr]">
        <ManufacturersCard />
        <ModelsCard />
      </div>
    </div>
  );
}

/** Inline text edit used for renaming catalog entries. */
function InlineName({
  value,
  onSave,
  label,
}: {
  value: string;
  onSave: (name: string) => Promise<void>;
  label: string;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  if (draft === null) {
    return (
      <span className="flex items-center gap-1">
        {value}
        <Button
          variant="ghost"
          size="icon"
          className="size-7"
          aria-label={`Renombrar ${label}`}
          onClick={() => setDraft(value)}
        >
          <Pencil className="size-3.5" />
        </Button>
      </span>
    );
  }
  const save = async () => {
    const name = draft.trim();
    if (!name || name === value) return setDraft(null);
    try {
      await onSave(name);
      setDraft(null);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };
  return (
    <span className="flex items-center gap-1">
      <Input
        className="h-8"
        value={draft}
        autoFocus
        aria-label={`Nuevo nombre de ${label}`}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") void save();
          if (e.key === "Escape") setDraft(null);
        }}
      />
      <Button
        variant="ghost"
        size="icon"
        className="size-8"
        aria-label="Guardar"
        onClick={() => void save()}
      >
        <Check />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="size-8"
        aria-label="Cancelar"
        onClick={() => setDraft(null)}
      >
        <X />
      </Button>
    </span>
  );
}

function ManufacturersCard() {
  const manufacturers = useManufacturers(true);
  const create = useCreateManufacturer();
  const update = useUpdateManufacturer();
  const [name, setName] = useState("");

  const add = async () => {
    try {
      await create.mutateAsync(name.trim());
      setName("");
      toast.success("Fabricante creado.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Fabricantes</CardTitle>
        <CardDescription>Los inactivos no aparecen al registrar equipos.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim()) void add();
          }}
        >
          <Input
            placeholder="Nuevo fabricante"
            value={name}
            onChange={(e) => setName(e.target.value)}
            aria-label="Nuevo fabricante"
          />
          <Button type="submit" variant="outline" disabled={!name.trim() || create.isPending}>
            <Plus /> Agregar
          </Button>
        </form>
        {manufacturers.isPending && <Skeleton className="h-40" />}
        <ul className="divide-y rounded-md border">
          {manufacturers.data?.map((m) => (
            <li key={m.id} className="flex items-center justify-between gap-2 px-3 py-1.5 text-sm">
              <InlineName
                value={m.name}
                label={m.name}
                onSave={async (newName) => {
                  await update.mutateAsync({ id: m.id, changes: { name: newName } });
                }}
              />
              <span className="flex items-center gap-1">
                {!m.is_active && <StatusBadge tone="neutral" label="Inactivo" />}
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-7"
                  aria-label={`${m.is_active ? "Desactivar" : "Activar"} ${m.name}`}
                  onClick={() =>
                    update
                      .mutateAsync({ id: m.id, changes: { is_active: !m.is_active } })
                      .catch((error: unknown) => toast.error(errorMessage(error)))
                  }
                >
                  <Power className="size-3.5" />
                </Button>
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function ModelsCard() {
  const categories = useCategories();
  const manufacturers = useManufacturers(true);
  const update = useUpdateModel();
  const [manufacturerId, setManufacturerId] = useState(ALL);
  const [category, setCategory] = useState(ALL);
  const [search, setSearch] = useState("");
  const models = useModels({
    manufacturer_id: manufacturerId || undefined,
    category: category || undefined,
    q: search.trim() || undefined,
    include_inactive: true,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Modelos</CardTitle>
        <CardDescription>Se muestran hasta 200 resultados; use los filtros.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="grid gap-3 sm:grid-cols-3">
          <SelectField
            label="Fabricante"
            value={manufacturerId}
            onChange={setManufacturerId}
            emptyLabel="Todos"
            options={(manufacturers.data ?? []).map((m) => ({ value: m.id, label: m.name }))}
          />
          <SelectField
            label="Categoría"
            value={category}
            onChange={setCategory}
            emptyLabel="Todas"
            options={(categories.data ?? []).map((c) => ({ value: c.code, label: c.name }))}
          />
          <div className="grid gap-1.5">
            <span className="text-sm font-medium">Buscar</span>
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Nombre del modelo"
              aria-label="Buscar modelo"
            />
          </div>
        </div>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Modelo</TableHead>
                <TableHead className="hidden sm:table-cell">Fabricante</TableHead>
                <TableHead className="hidden sm:table-cell">Categoría</TableHead>
                <TableHead className="w-24">
                  <span className="sr-only">Estado</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {models.data?.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-muted-foreground py-6 text-center">
                    No hay modelos. Se crean al registrar equipos.
                  </TableCell>
                </TableRow>
              )}
              {models.data?.map((model) => (
                <TableRow key={model.id}>
                  <TableCell>
                    <InlineName
                      value={model.name}
                      label={model.name}
                      onSave={async (name) => {
                        await update.mutateAsync({ id: model.id, changes: { name } });
                      }}
                    />
                  </TableCell>
                  <TableCell className="hidden text-sm sm:table-cell">
                    {model.manufacturer.name}
                  </TableCell>
                  <TableCell className="hidden text-sm sm:table-cell">
                    {model.category.name}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        update
                          .mutateAsync({ id: model.id, changes: { is_active: !model.is_active } })
                          .catch((error: unknown) => toast.error(errorMessage(error)))
                      }
                    >
                      {model.is_active ? "Desactivar" : "Activar"}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
