import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

import { createProject } from "@/lib/api";

interface CreateProjectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateProjectModal({ open, onOpenChange }: CreateProjectModalProps) {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    repoName: "",
    githubToken: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Validate fields
    if (!formData.repoName || !formData.githubToken) {
      toast.error("Please fill in all fields");
      setLoading(false);
      return;
    }

    try {
      // Extract owner/repo if full URL is provided
      let repo = formData.repoName;
      if (repo.includes("github.com/")) {
        repo = repo.split("github.com/")[1].split("/").slice(0, 2).join("/");
      }
      
      const data = await createProject(repo, formData.githubToken);
      console.log("Created project:", data);

      toast.success("Project added successfully!");
      onOpenChange(false);
      // Reset form
      setFormData({
        repoName: "",
        githubToken: "",
      });
    } catch (error: any) {
      console.error("Project creation error:", error);
      toast.error(`Failed to add repository: ${error.message || "Unknown error"}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] bg-card border-border">
        <DialogHeader>
          <DialogTitle className="text-foreground">Add Repository</DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Connect a GitHub repository to enable autonomous healing.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="repo" className="text-muted-foreground uppercase text-[10px] tracking-wider">
              GitHub Repo (owner/repo)
            </Label>
            <Input
              id="repo"
              placeholder="e.g. google/ascent"
              value={formData.repoName}
              onChange={(e) => setFormData({ ...formData, repoName: e.target.value })}
              className="bg-background border-border"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="token" className="text-muted-foreground uppercase text-[10px] tracking-wider">
              GitHub Personal Access Token
            </Label>
            <Input
              id="token"
              type="password"
              placeholder="ghp_xxxxxxxxxxxx"
              value={formData.githubToken}
              onChange={(e) => setFormData({ ...formData, githubToken: e.target.value })}
              className="bg-background border-border"
            />
            <p className="text-[10px] text-muted-foreground">
              Token needs 'repo' and 'admin:repo_hook' scopes.
            </p>
          </div>
          <DialogFooter className="pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="border-border hover:bg-muted"
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading} className="bg-primary text-primary-foreground hover:opacity-90">
              {loading ? "Adding..." : "Add Repository"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
