# Code Architect
A tool to generate report to understand large codebases it terms of its dependency structure matrix


This tool compute following for a given codabase (or group of codebase all present in a single folder).

1. Size metrics - using tokei and ctags
2. Cyclomatic Complexity metric - using lizard
3. Dependency Structure Matrix - computed using pygments under the hood
4. Layers - like lattix using custom algorithms and tarjan
5. Wordcloud - topic analysis
6. Techstack - external libraries, tools, language, sorted by most used
7. Git stats - summary, effort, count, fame, quick-stats, git-sizer
8. Commit message analysis

## References

* https://github.com/arzzen/git-quick-stats
* https://github.com/casperdcl/git-fame
* https://github.com/tj/git-extras
* https://github.com/github/semantic
* https://github.com/donovanhiland/atom-file-icons
* https://github.com/github/super-linter
* https://github.blog/2018-03-05-measuring-the-many-sizes-of-a-git-repository/
* https://sci-hub.do/10.1145/2597073.2597118
* https://medium.com/@sAbakumoff/angular-vs-react-text-analysis-of-commit-messages-1cda199f3bdb
* https://eazybi.com/integrations/git
* https://homepages.dcc.ufmg.br/~mirella/ppt/2017-WI-Batista.pdf




