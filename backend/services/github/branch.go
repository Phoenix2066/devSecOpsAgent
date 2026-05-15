package github

func CreateBranch(repo RepoRef, baseSHA, branchName string) BranchRef {
	return BranchRef{Name: branchName, SHA: baseSHA}
}

func CommitFiles(repo RepoRef, branch, message string, files map[string]string) string {
	return "mock-commit-sha"
}

func OpenPR(repo RepoRef, head, base, title, body string) PRRef {
	return PRRef{URL: "https://github.com/" + repo.Owner + "/" + repo.Repo + "/pull/mock"}
}
