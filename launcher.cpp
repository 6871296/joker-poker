#include<cstring>
#include<vector>
#include<string>
#include<iostream>
#include<cstdio>
#include<sys/wait.h>
#include<queue>
#include<algorithm>
#include<fstream>
#include<sstream>
using namespace std;
const char TAB='	';

string ver_max(string v1,string v2){
    if(v1==v2)return v1;
    queue<int>v1q,v2q;
    string ver="";
    for(char c:v1){
        if(c=='.'){
            v1q.push(stoi(ver));
            ver="";
        }else ver+=c;
    }
    ver="";
    for(char c:v2){
        if(c=='.'){
            v2q.push(stoi(ver));
            ver="";
        }else ver+=c;
    }
    if(v1q.front()>v2q.front())return v1;
    else{
        v1q.pop();
        v2q.pop();
        if(v1q.front()>v2q.front())return v1;
        else{
            v1q.pop();
            v2q.pop();
            if(v1q.front()>v2q.front())return v1;
            else return v2;
        }
    }
}
bool run(string model){
    #if defined(_WIN32)||defined(_WIN64)
        //py -0

        FILE* pipe = _popen("py -0 2>nul", "r");
        
        if (!pipe) {
            // 如果连指令都发不出去，这是严重错误，可以报错一下
            cerr << "\033[0;1;31mFailed to list Python versions!\033[0m" << endl;
            return 1;
        }

        char buffer[128];
        string latestVersionCommand = "";

        // 循环读取每一行
        while (fgets(buffer, sizeof(buffer), pipe) != NULL) {
            string line = buffer;

            // 我们要找带有 * 星号的行，因为那代表当前默认/最新的激活版本
            if (line.find('*') != string::npos) {
                // 解析命令行参数，比如 "-V:3.11"
                // 找到冒号的位置
                size_t colonPos = line.find(':');
                
                if (colonPos != string::npos) {
                    // 提取版本参数
                    // 从冒号后面开始找，找到空格或者结束为止
                    size_t start = colonPos + 1;
                    size_t end = line.find(' ', start);
                    
                    if (end == string::npos) {
                        // 如果没找到空格（比如到了行尾），就截取到末尾
                        // 注意：fgets 会读取换行符，我们要手动截掉末尾的 '\n' 或 ' '
                        if (!line.empty() && line.back() == '\n') line.pop_back();
                        if (!line.empty() && line.back() == ' ') line.pop_back();
                        latestVersionCommand = line.substr(start);
                    } else {
                        latestVersionCommand = line.substr(start, end - start);
                    }
                    
                    // 拼接成完整的启动指令
                    latestVersionCommand = "py -V:" + latestVersionCommand;
                    
                    // 找到最新的带 * 的版本后，直接跳出循环，不用再读下面的了
                    break; 
                }
            }
        }

        int status = _pclose(pipe);
        if(status!=0){
            cerr << "\033[0;1;31mFailed to list Python versions!\033[0m" << endl;
            return 1;
        }

        // 如果成功找到了版本命令
        if (!latestVersionCommand.empty()) {
            // 为了防止窗口一闪而过，我们加上 " && pause"
            // 这意味着：启动 Python，当 Python 退出后，执行 pause 暂停一下
            system((latestVersionCommand + " ./" +model.c_str()+" && pause").c_str());
        } else {
            // 如果没找到（比如列表为空，或者没有 * 号）
            cout<<"No Python version found. Do you want to dawnload Python3.14? (y/n)";
            while(c=='y'||c=='n'){
                char c;
                cin>>c;
            }if(c=='y'){
                system("wget https://www.python.org/ftp/python/3.14.3/python-3.14.3-amd64.exe -O pyinstall.exe");
                system("pyinstall.exe");
                system("rm pyinstall.exe");
                run(model);
            }else return;
        }
        return 0;
    #else
        FILE* pipe = popen("ls /Library/Frameworks/Python.framework/Versions", "r");
        if(!pipe){
            cerr << "\033[0;1;31mFailed to list Python versions!\033[0m" << endl;
            return 1;
        }
        char buffer[128];
        string maxVer="0";
        // 循环读取每一行
        while (fgets(buffer, sizeof(buffer), pipe) != NULL) {
            string line = buffer;
            string ver="";
            for(char c:line){
                if(c==TAB||c=='\n'||c==EOF){
                    if(ver=="Current")break;
                    if(ver!="")maxVer=ver_max(maxVer,ver);
                    ver="";
                }else ver+=c;
            }
        }
        int status=pclose(pipe);
        if(WIFEXITED(status)){
            if(WEXITSTATUS(status)!=0){
                cerr << "\033[0;1;31mFailed to list Python versions!\033[0m" << endl;
                return 1;
            }
        }else{
            cerr << "\033[0;1;31mFailed to list Python versions!\033[0m" << endl;
            return 1;
        }
    #endif
    return 0;
}
string readFile(string path){
    ifstream file(path);
    stringstream buffer;
    buffer<<file.rdbuf();
    return buffer.str();
}
bool runm(string model,int argc,char* argv[]){
    for(int i=0;i<argc;i++){
        if(strcmp(argv[i],"-v")==0){
            cout<<readFile("configs/"+model+".version.cfg")<<endl;
            return 0;
        }
    }
    return run(model+".py");
}
int main(int argc,char* argv[]){
    if(argc==0)
        if(run("app.py"))
            return 1;
    else{
        for(int i=1;i<argc;i++){
            if(strcmp(argv[i],"-v")==0){
                cout<<readFile("configs/main.version.cfg")<<endl;
                return 0;
            }
            if(strcmp(argv[i],"-m")==0){
                runm(argv[i+1],argc-i-2,argv+i+2);
            }
        }
    }
}